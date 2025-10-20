from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from limits.strategies import FixedWindowRateLimiter
from datetime import datetime,timedelta
from limits.storage import RedisStorage
import math
from schemas.response_schema import APIResponse
from repositories.tokens_repo import get_access_tokens_no_date_check
from limits import parse
import time   
import os
from celery_worker import celery_app
from contextlib import asynccontextmanager
from core.scheduler import scheduler



@asynccontextmanager
async def lifespan(app:FastAPI):
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()
    

class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Record the start time before processing the request
        start_time = time.time()
        
        # Process the request and get the response
        response = await call_next(request)
        
        # Calculate the time taken to process the request
        process_time = time.time() - start_time
        
        # You can log the time or set it in the response headers
        response.headers['X-Process-Time'] = str(process_time)
        
        # Optionally, print it for logging purposes
        print(f"Request to {request.url} took {process_time:.6f} seconds")
        
        return response
    
    
    

 

    
# Create the FastAPI app
app = FastAPI(
    lifespan= lifespan,
    title="REST API",
)
app.add_middleware(RequestTimingMiddleware)
# Setup limiter
storage = RedisStorage(
    "redis://localhost:6379/0"
)

limiter = FixedWindowRateLimiter(storage)

RATE_LIMITS = {
    "annonymous": parse("20/minute"),
    "member": parse("60/minute"),
    "admin": parse("140/minute"),
}

async def get_user_type(request: Request) -> tuple[str, str]:
    """
    Return a tuple of (user_identifier, user_type)
    You can extract from JWT, headers, or session.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        ip_address = request.headers.get("X-Forwarded-For", request.client.host)
        user_id = ip_address
        user_type="annonymous"
        return user_id, user_type if user_type in RATE_LIMITS else "annonymous"
    
    
    token = auth_header.split(" ")[1] 
    access_token  =await get_access_tokens_no_date_check(accessToken=token)
    
    user_id = access_token.userId
    
    user_type = access_token.role

 
    return user_id, user_type if user_type in RATE_LIMITS else "annonymous"

class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id, user_type = await get_user_type(request)
        rate_limit_rule = RATE_LIMITS[user_type]

        # hit() → True if still under limit
        allowed = limiter.hit(rate_limit_rule, user_id)

        # Get current window stats (reset_time, remaining)
        reset_time, remaining = limiter.get_window_stats(rate_limit_rule, user_id)
        seconds_until_reset = max(math.ceil(reset_time - time.time()), 0)

        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={
                    "X-User-Type": user_type,
                    "X-User-Id":user_id,
                    "X-RateLimit-Limit": str(rate_limit_rule.amount),
                    "X-RateLimit-Remaining": str(max(remaining, 0)),
                    "X-RateLimit-Reset": str(seconds_until_reset),
                    "Retry-After": str(seconds_until_reset),
                },
                content=APIResponse(
                    status_code=429,
                    data={
                        "retry_after_seconds": seconds_until_reset,
                        "user_type": user_type,
                    },
                    detail="Too Many Requests",
                ).dict(),
            )

        # Normal flow
        response = await call_next(request)

        # Add rate-limit headers for successful requests too
        response.headers["X-User-Id"]=user_id
        response.headers["X-User-Type"] = user_type
        response.headers["X-RateLimit-Limit"] = str(rate_limit_rule.amount)
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))
        response.headers["X-RateLimit-Reset"] = str(seconds_until_reset)

        return response

# Add the middleware to the app
# ||||||||||||||||||||||||||||||||||||

app.add_middleware(RateLimitingMiddleware)

# ||||||||||||||||||||||||||||||||||||

# Add CORS middleware (be cautious in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for HTTPExceptions
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            status_code=exc.status_code,
            data=None,
            detail=exc.detail,
        ).dict()
    )

async def test_scheduler(message):
    print(message)
# Simple test route

@app.get("/test-celery")
async def test_celery():
    result = celery_app.send_task("celery_worker.test_scheduler", args=["Messageeee"])
    return {"task_id": result.id}
   
@app.get("/")
def read_root():
    run_time = datetime.now() + timedelta(seconds=20)
    scheduler.add_job(test_scheduler,"date",run_date=run_time,args=[f"test message {run_time}"],misfire_grace_time=31536000)
    
    return {"message": "Hello from FasterAPI!"}

# Health check route
@app.get("/health")
async def health_check():
    return {"status": "healthy"}