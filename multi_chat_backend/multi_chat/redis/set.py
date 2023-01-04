from typing import Any, Generic, TypeVar, get_args

from pydantic import BaseModel, parse_raw_as
from pydantic.generics import GenericModel

from multi_chat import config

from . import get_database

T = TypeVar("T", bound=BaseModel)


class RedisSet(Generic[T], GenericModel):

    _type_T: Any

    def __init_subclass__(cls) -> None:
        cls._type_T = get_args(cls.__orig_bases__[0])[0]  # type: ignore

    @classmethod
    def get_key(cls) -> str:
        return config.redis.redis_prefix + ":" + str(cls.__name__)

    @classmethod
    async def add(cls, item: T) -> bool:
        return await get_database().sadd(cls.get_key(), item.json().encode(encoding="utf8")) # type: ignore
    
    @classmethod
    async def remove(cls, item: T) -> bool:
        return await get_database().srem(cls.get_key(), item.json().encode(encoding="utf8")) # type: ignore

    @classmethod
    async def exists(cls, item: T) -> bool:
        return await get_database().sismember(cls.get_key(), item.json().encode(encoding="utf8")) # type: ignore

    @classmethod
    async def count(cls) -> int:
        return await get_database().scard(cls.get_key()) # type: ignore

    @classmethod
    async def random_get(cls) -> T:   # type: ignore
        obj = await get_database().srandmember(cls.get_key()) # type: ignore
        return parse_raw_as(cls._type_T, obj, encoding="utf8") if obj else None   # type: ignore


