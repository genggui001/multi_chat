from typing import Optional

from ..redis import RedisCache
from .models import GPT3DialogHistory


class GPT3DialogStateCache(RedisCache[GPT3DialogHistory]):
    pass


