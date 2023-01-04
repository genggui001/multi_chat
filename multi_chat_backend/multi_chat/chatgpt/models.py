from typing import Optional, Union
from uuid import UUID

from ..mongo import MongoModel


class ChatGPTDialogHistory(MongoModel):

    session_id: UUID
    dhid: UUID

    openai_account_email: Optional[str] = None
    openai_conversation_id: Optional[str] = None
    openai_previous_convo_id: Optional[str] = None

    @classmethod
    def collection_name(cls) -> str:
        return "chatgpt_dialog_history"



