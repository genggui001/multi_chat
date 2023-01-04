from typing import Optional

from aredis import StrictRedis

from multi_chat import config

_client: Optional[StrictRedis] = None

async def create_connection():
    global _client
    _client = StrictRedis.from_url(
        url=config.redis.redis_url,
        decode_responses=False
    )

def get_database() -> StrictRedis:
    if _client is None:
        raise ValueError("Redis connection has not been initialized.")
    return _client

from .cache import RedisCache
from .set import RedisSet
