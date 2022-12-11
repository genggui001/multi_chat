import json
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from multi_chat.mongo.dialog_info import get_one_dialog_info
from multi_chat.mongo.models import User
from multi_chat.mongo.user import get_current_active_user
from pydantic import BaseModel

router = APIRouter()


class RequestModel(BaseModel):
    conversation_id: UUID
    message_id: UUID
    rating: str
    tags: List[str] = []
    text: str = ""
    

class ResponseModel(BaseModel):
    conversation_id: UUID
    message_id: UUID
    rating: str
    content: str
    user_id: str


@router.post("/conversation/message_feedback", response_model=ResponseModel)
async def feedback(
    data: RequestModel,
    # current_user: User = Depends(get_current_active_user),
) -> ResponseModel:

    session_id = data.conversation_id
    dhid = data.message_id

    # 获取所有历史信息
    dialog_info = await get_one_dialog_info(
        session_id=session_id,
        dhid=dhid
    )

    assert dialog_info is not None

    if data.rating == 'thumbsUp':
        dialog_info.user_feedback_rank = 10
    else:
        dialog_info.user_feedback_rank = -10

    dialog_info.user_feedback_content = json.dumps({
        "text": data.text,
        "tags": data.tags,
    }, ensure_ascii=False)

    save_re = await dialog_info.save()

    assert save_re == 0 or save_re == 1

    return ResponseModel(
        conversation_id=data.conversation_id,
        message_id=data.message_id,
        rating=data.rating,
        content=dialog_info.user_feedback_content,
        user_id="user-0F68QjP4ORZ9XZOOwm4EjGzL",
    )
