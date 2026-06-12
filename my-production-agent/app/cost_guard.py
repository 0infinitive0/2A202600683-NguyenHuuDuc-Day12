import redis
from datetime import datetime
from fastapi import HTTPException, Depends
from .config import settings
from .auth import verify_api_key

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def check_budget(user_id: str = Depends(verify_api_key)):
    current_month = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{current_month}"
    
    # Mock cost per request (e.g., $0.05)
    cost_per_request = 0.05
    
    current_spend = redis_client.get(key)
    if current_spend and float(current_spend) >= settings.MONTHLY_BUDGET_USD:
        raise HTTPException(status_code=402, detail="Monthly budget exceeded")
        
    redis_client.incrbyfloat(key, cost_per_request)
    redis_client.expire(key, 31 * 24 * 60 * 60)  # Expire after 31 days