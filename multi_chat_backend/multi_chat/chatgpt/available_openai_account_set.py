from pydantic import BaseModel

from ..redis import RedisSet


class AvailableOpenAIAccount(BaseModel):
    email: str

class AvailableOpenAIAccountSet(RedisSet[AvailableOpenAIAccount]):
    pass


