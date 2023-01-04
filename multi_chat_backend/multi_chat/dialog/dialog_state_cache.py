from typing import Optional

from ..redis import RedisCache
from .models import DialogHistory


class DialogStateCache(RedisCache[DialogHistory]):
    pass


