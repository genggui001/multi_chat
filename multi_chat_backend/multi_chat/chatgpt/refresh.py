import traceback

from fastapi import APIRouter
from multi_chat.chatgpt import get_chatgpt_client
from multi_chat.models import ResponseCode, ResponseWrapper
from pydantic import BaseModel

from multi_chat import config, logger

router = APIRouter()


class RequestModel(BaseModel):
    refresh_passwd: str

class ResponseModel(BaseModel):
    reply: str


@router.post("/chatgpt", response_model=ResponseWrapper[ResponseModel])
async def chatgpt(
    data: RequestModel
) -> ResponseWrapper[ResponseModel]:
    
    try:
        if data.refresh_passwd != config.chatgpt.refresh_passwd:
            return ResponseWrapper(
                code=ResponseCode.success,
                result=ResponseModel(
                    reply="refresh passwd incompatible"
                )
            )

        await get_chatgpt_client()._refresh_all_accounts()

        return ResponseWrapper(
            code=ResponseCode.success,
            result=ResponseModel(
                reply="success"
            )
        )

    except Exception as e:

        if config.fastapi.debug == True:
            raise e
        
        logger.warning(traceback.format_exc())

        return ResponseWrapper(
            code=ResponseCode.internal_error,
            result=ResponseModel(
                reply=traceback.format_exc()
            )
        )
