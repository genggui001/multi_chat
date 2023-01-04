import json
import traceback
from typing import List, Optional, Union
from uuid import UUID, uuid1

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from multi_chat.models import ResponseCode, ResponseWrapper
# from multi_chat.mongo.models import User
# from multi_chat.mongo.user import get_current_active_user
from pydantic import BaseModel

from multi_chat import logger

from .chat_client import get_chat_client
from .dialog_info import (get_now_dialog_info,
                          save_new_dialog_info_and_update_now)

router = APIRouter()

class RequestContentModel(BaseModel):
    content_type: str
    parts: List[str]


class RequestMessageModel(BaseModel):
    id: UUID
    role: str
    content: RequestContentModel


class RequestModel(BaseModel):
    action: str
    model: str
    messages: List[RequestMessageModel]
    conversation_id: Optional[UUID] = None
    parent_message_id: Optional[UUID] = None

    

class ResponseModel(BaseModel):
    reply: str
    now_dhid: Optional[UUID] = None


@router.post("/conversation")
async def conversation(
    data: RequestModel,
    # current_user: User = Depends(get_current_active_user),
) -> Union[StreamingResponse, ResponseWrapper[ResponseModel]]:
    try:
        #当前句子
        sentence_text = "".join([
            "".join(message.content.parts)
            for message in data.messages
        ])
        # 保存逻辑修正
        if data.conversation_id is None:
            session_id = uuid1()
            previous_dhid = None
        else:
            session_id = data.conversation_id
            previous_dhid = data.parent_message_id

        round_id = 0

        assert len(sentence_text) > 0, "need len(sentence_text) > 0"

        # 获取所有历史信息
        last_dialog_info = await get_now_dialog_info(
            session_id=session_id,
            dhid=previous_dhid
        )

        if last_dialog_info is not None:
            previous_dhid = last_dialog_info.dhid
            round_id = last_dialog_info.round_id + 1


        # 手动尝试第一次迭代

        chat_client = get_chat_client(data.model)

        r_iter = chat_client.ask(
            prompt=sentence_text,
            session_id=session_id,
            previous_dhid=previous_dhid,
        )

        answer, _, now_dhid = await r_iter.__anext__()

        # 重新封装返回器
        async def response_generator():
            nonlocal answer
            nonlocal now_dhid

            try:
                # 伪装第一次空白返回
                yield (b"data: " + json.dumps({
                    "message":{
                        "id": str(now_dhid),
                        "role":"assistant",
                        "user": None,
                        "create_time":None,
                        "update_time":None,
                        "content":{
                            "content_type":"text",
                            "parts": []
                        },
                        "end_turn":None,
                        "weight":1,
                        "metadata":{},
                        "recipient":"all"
                    },
                    "conversation_id": str(session_id),
                    "error":None
                }, ensure_ascii=False).encode("utf8") + b"\n\n")

                # 正常循环启动
                while True:
                    yield (b"data: " + json.dumps({
                        "message":{
                            "id": str(now_dhid),
                            "role":"assistant",
                            "user": None,
                            "create_time":None,
                            "update_time":None,
                            "content":{
                                "content_type":"text",
                                "parts": [answer]
                            },
                            "end_turn":None,
                            "weight":1,
                            "metadata":{},
                            "recipient":"all"
                        },
                        "conversation_id": str(session_id),
                        "error":None
                    }, ensure_ascii=False).encode("utf8") + b"\n\n")

                    answer, _, now_dhid = await r_iter.__anext__()

            except StopAsyncIteration:
                pass

            # 关闭迭代器
            await r_iter.aclose()

            # 保存最后一轮
            await save_new_dialog_info_and_update_now(
                session_id=session_id,
                round_id=round_id,

                ask_text=sentence_text,
                answer_text=answer,

                dhid=now_dhid,
                previous_dhid=previous_dhid,
            )

            yield b"data: [DONE]\n\n"

        return StreamingResponse(
            content=response_generator(),
            status_code=200,
            media_type="text/event-stream",
        )

    except:
        try:
            # 关闭迭代器
            await r_iter.aclose() # type: ignore
        except:
            pass

        error_text = traceback.format_exc()
        logger.warning("Error:\n" + error_text)
        return ResponseWrapper(
            code=ResponseCode.internal_error,
            result=ResponseModel.parse_obj(dict(
                reply=error_text,
                now_dhid=None,
            )),
        )
