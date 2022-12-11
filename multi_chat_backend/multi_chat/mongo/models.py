from typing import Optional
from uuid import UUID

from . import MongoModel


class DialogHistory(MongoModel):
    dhid: UUID
    previous_dhid: Optional[UUID] = None

    session_id: UUID
    round_id: int

    ask_text: str
    answer_text: str
    answer_timestamp: int
    
    user_feedback_rank: int = 0
    user_feedback_content: str = ""

    openai_account_email: Optional[str] = None
    openai_conversation_id: Optional[str] = None
    openai_previous_convo_id: Optional[str] = None

    @classmethod
    def collection_name(cls) -> str:
        return "dialog_history"



