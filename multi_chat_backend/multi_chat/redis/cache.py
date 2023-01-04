from typing import Any, Generic, Optional, TypeVar, get_args

from pydantic import BaseModel, parse_raw_as
from pydantic.generics import GenericModel

from multi_chat import config

from . import get_database

T = TypeVar("T", bound=BaseModel)


class RedisCache(Generic[T], GenericModel):

    _type_T: Any

    def __init_subclass__(cls) -> None:
        cls._type_T = get_args(cls.__orig_bases__[0])[0]  # type: ignore

    @classmethod
    def format_key(cls, key: str) -> str:
        return config.redis.redis_prefix + ":" + str(cls.__name__) + "__" + key

    @classmethod
    async def get(cls, key: str) -> Optional[T]: # type: ignore
        obj = await get_database().get(cls.format_key(key)) # type: ignore
        return parse_raw_as(cls._type_T, obj, encoding="utf8") if obj else None   # type: ignore
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        return await get_database().exists(cls.format_key(key)) # type: ignore

    @classmethod
    async def delete(cls, key: str) -> bool:
        return await get_database().execute_command("del", cls.format_key(key)) # type: ignore
        
    @classmethod
    async def set(
        cls, 
        key: str, 
        value: T,
        ex: Optional[int] = None,
    ):
        await get_database().set(cls.format_key(key), value.json().encode(encoding="utf8"), ex=ex) # type: ignore
