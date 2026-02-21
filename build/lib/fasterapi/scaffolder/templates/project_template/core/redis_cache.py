import redis
import os

cache_db = redis.Redis(
    host=os.getenv("REDIS_HOST"), # type: ignore
    port=int(os.getenv("REDIS_PORT")), # type: ignore
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
   decode_responses=True
)