from typing import Optional

from pydantic import BaseModel

from ..redis import RedisCache


class OpenAIAccount(BaseModel):
    email: str
    password: str
    access_token: Optional[str]
    expiry: Optional[int]
    proxy: Optional[str]
    # available: bool = True



class OpenAIAccountCache(RedisCache[OpenAIAccount]):
    pass




