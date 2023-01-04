from enum import IntEnum
from typing import Generic, Optional, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel
from pydantic.generics import GenericModel

R = TypeVar("R", bound=BaseModel)


class ResponseCode(IntEnum):
    success = 0
    empty_result = 10
    internal_error = 20


class ResponseWrapper(GenericModel, Generic[R]):
    code: ResponseCode = ResponseCode.success
    result: R


# DialogHistoryR = TypeVar("DialogHistoryR", bound=BaseModel)

# class DialogHistoryWrapper(GenericModel, Generic[DialogHistoryR]):
#     dhid: UUID
#     previous_dhid: Optional[UUID] = None

#     session_id: UUID
#     round_id: int

#     ask_text: str
#     answer_text: str
#     answer_timestamp: int
    
#     user_feedback_rank: int = 0
#     user_feedback_content: str = ""

#     # dialog_history_data_type: str = str(Type[DialogHistoryR].__name__)
#     dialog_history_data: DialogHistoryR
    

