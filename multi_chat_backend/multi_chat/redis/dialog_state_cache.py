from typing import Optional

from multi_chat.mongo import DialogHistory

from . import get_database


class DialogStateCache:
    key_prefix = "multi_chat_gpt:dialog_state"
    value_model = DialogHistory

    @classmethod
    def format_key(cls, key: str) -> str:
        return cls.key_prefix + "__" + key

    @classmethod
    async def get(cls, key: str) -> Optional[DialogHistory]:
        obj = await get_database().get(cls.format_key(key)) # type: ignore
        return cls.value_model.parse_raw(obj, encoding="utf8") if obj else None
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        return await get_database().exists(cls.format_key(key)) # type: ignore

    @classmethod
    async def set(
        cls, 
        key: str, 
        value: DialogHistory,
        ex: Optional[int] = None,
    ):
        await get_database().set(cls.format_key(key), value.json().encode(encoding="utf8"), ex=ex) # type: ignore

    




