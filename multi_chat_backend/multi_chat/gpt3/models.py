from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel

from ..mongo import MongoModel


class GPT3DialogHistory(MongoModel):

    session_id: UUID
    dhid: UUID

    openai_account_email: Optional[str] = None
    pre_text: Optional[str] = None

    @classmethod
    def collection_name(cls) -> str:
        return "gpt3_dialog_history"


class OpenAIAccount(BaseModel):
    email: str
    access_token: str
