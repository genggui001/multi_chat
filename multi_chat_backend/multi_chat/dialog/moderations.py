import json
from typing import List
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from multi_chat.models import ResponseCode, ResponseWrapper
from multi_chat.mongo.dialog_info import get_one_dialog_info

router = APIRouter()


class RequestModel(BaseModel):
    input: str = ""
    model: str = ""
    

class ResponseModel(BaseModel):
    blocked: bool = False
    flagged: bool = False
    moderation_id: str = ""


@router.post("/moderations", response_model=ResponseModel)
async def feedback(
    data: RequestModel
) -> ResponseModel:

    return ResponseModel(
        blocked=False,
        flagged=False,
        moderation_id="",
    )

