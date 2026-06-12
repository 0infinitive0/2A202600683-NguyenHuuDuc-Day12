import redis
from fastapi import HTTPException, Depends
import time
from .config import settings
from .auth import verify_api_key

r = redis.from_url(settings.REDIS_URL, decode_responses=True)

def check_rate_limit(user_id: str = Depends(verify_api_key)):
    now = time.time()
    window_start = now - 60
    key = f"rate_limit:{user_id}"
    
    pipe = r.pipeline()
    # Remove requests older than 60 seconds
    pipe.zremrangebyscore(key, 0, window_start)
    # Count requests in the current window
    pipe.zcard(key)
    # Add the current request
    pipe.zadd(key, {str(now): now})
    # Expire to prevent memory leaks if the user stops sending requests
    pipe.expire(key, 60)
    
    results = pipe.execute()
    request_count = results[1]
    
    if request_count >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")