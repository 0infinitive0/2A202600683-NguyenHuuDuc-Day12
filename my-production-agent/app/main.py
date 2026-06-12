from fastapi import FastAPI, Depends, HTTPException
from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import check_budget

import time
import redis
from pydantic import BaseModel

try:
    from utils.mock_llm import ask as llm_ask
except ImportError:
    # Fallback to avoid breaking if utils cannot be resolved directly
    def llm_ask(q: str): return f"Mock answer for: {q}"

app = FastAPI()

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
START_TIME = time.time()

class AskRequest(BaseModel):
    question: str
    user_id: str = "default"  # Handled natively, but Depends(verify_api_key) will confirm auth

@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1)
    }

@app.get("/ready")
def ready():
    try:
        redis_client.ping()
        return {"ready": True}
    except redis.ConnectionError:
        raise HTTPException(status_code=503, detail="Redis connection failed")

@app.post("/ask")
def ask(
    request: AskRequest,
    user_id: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget)
):
    history_key = f"chat_history:{user_id}"
    
    # 1. Get conversation history from Redis
    history = redis_client.lrange(history_key, 0, -1)
    
    # 2. Call LLM
    answer = llm_ask(request.question)
    
    # 3. Save to Redis
    redis_client.rpush(history_key, f"User: {request.question}")
    redis_client.rpush(history_key, f"Agent: {answer}")
    redis_client.expire(history_key, 3600)  # Keep history for 1 hour
    
    # 4. Return response
    return {
        "question": request.question,
        "answer": answer,
        "history_length": len(history) // 2 + 1
    }