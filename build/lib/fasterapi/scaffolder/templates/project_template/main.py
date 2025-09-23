from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from limits import Limiter, RateLimitItemPerMinute
from limits.storage import MemoryStorage
from limits.errors import RateLimitExceeded
from schemas.response_schema import APIResponse
import time   

# Create the FastAPI app
app = FastAPI()

# Setup limiter
storage = MemoryStorage()
limiter = Limiter(storage)

# Define rate limits per user type Change the logic here to be more dynamic or not
RATE_LIMITS = {
    "free": RateLimitItemPerMinute(5),
    "premium": RateLimitItemPerMinute(20),
    "admin": RateLimitItemPerMinute(100),
}

# Dummy user resolution function (replace with function to actually get user from the request object)
def get_user_type(request: Request) -> tuple[str, str]:
    """
    Return a tuple of (user_identifier, user_type)
    You can extract from JWT, headers, or session.
    """
    user_id = request.headers.get("X-User-ID", "anonymous")
    user_type = request.headers.get("X-User-Type", "free").lower()
    return user_id, user_type if user_type in RATE_LIMITS else "free"

class RateLimitingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id, user_type = get_user_type(request)
        rate_limit_rule = RATE_LIMITS[user_type]

        try:
            # Use user_id as the rate limit key
            limiter.hit(rate_limit_rule, user_id)

            response = await call_next(request)
            return response

        except RateLimitExceeded:
            # Get time until the limit resets
            _, reset_time = limiter.get_window_stats(rate_limit_rule, user_id)
            current_time = int(time.time())
            seconds_until_reset = max(reset_time - current_time, 0)

            return JSONResponse(
                status_code=429,
                content=APIResponse(
                    status_code=429,
                    data={
                        "retry_after_seconds": seconds_until_reset,
                        "user_type": user_type
                    },
                    detail="Too Many Requests"
                ).dict()
            )

# Add the middleware to the app
# ||||||||||||||||||||||||||||||||||||

# app.add_middleware(RateLimitingMiddleware)

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

# Simple test route
@app.get("/")
def read_root():
    return {"message": "Hello from FasterAPI!"}

# Health check route
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
