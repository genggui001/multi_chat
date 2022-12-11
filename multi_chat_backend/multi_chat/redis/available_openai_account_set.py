from . import get_database


class AvailableOpenAIAccountSet:
    key = "multi_chat_gpt:available_openai_account_set"

    @classmethod
    async def add(cls, item: str) -> bool:
        return await get_database().sadd(cls.key, item.encode(encoding="utf8")) # type: ignore
    
    @classmethod
    async def remove(cls, item: str) -> bool:
        return await get_database().srem(cls.key, item.encode(encoding="utf8")) # type: ignore

    @classmethod
    async def exists(cls, item: str) -> bool:
        return await get_database().sismember(cls.key, item.encode(encoding="utf8")) # type: ignore

    @classmethod
    async def count(cls) -> int:
        return await get_database().scard(cls.key) # type: ignore

    @classmethod
    async def random_get(cls) -> str:
        item = await get_database().srandmember(cls.key) # type: ignore
        return  item.decode(encoding="utf8") if item is not None else None # type: ignore





