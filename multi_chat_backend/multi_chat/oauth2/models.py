from typing import Union

from ..mongo import MongoModel


class User(MongoModel):
    username: str
    hashed_password: str
    disabled: Union[bool, None] = None

    @classmethod
    def collection_name(cls) -> str:
        return "user"
