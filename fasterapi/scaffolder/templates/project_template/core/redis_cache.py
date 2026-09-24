import redis

from core.settings import get_settings

cache_db = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
