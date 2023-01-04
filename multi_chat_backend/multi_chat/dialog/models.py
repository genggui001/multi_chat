from enum import IntEnum
from typing import Generic, Optional, Type, TypeVar
from uuid import UUID

from ..mongo import MongoModel

# from pydantic import BaseModel



class DialogHistory(MongoModel):
    session_id: UUID
    dhid: UUID
    previous_dhid: Optional[UUID] = None

    round_id: int

    ask_text: str
    answer_text: str
    answer_timestamp: int
    
    user_feedback_rank: int = 0
    user_feedback_content: str = ""

    @classmethod
    def collection_name(cls) -> str:
        return "dialog_history"

