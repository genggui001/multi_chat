from typing import Optional

from ..redis import RedisCache
from .models import ChatGPTDialogHistory


class ChatGPTDialogStateCache(RedisCache[ChatGPTDialogHistory]):
    pass


