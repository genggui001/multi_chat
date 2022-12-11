import json
import traceback
from typing import Optional, Union
from uuid import UUID, uuid1

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from multi_chat import logger
from multi_chat.chatgpt import get_chatgpt_client
from multi_chat.models import ResponseCode, ResponseWrapper
from multi_chat.mongo.dialog_info import (get_now_dialog_info,
                                          save_new_dialog_info_and_update_now)
from multi_chat.session import get_session_id

router = APIRouter()


class RequestModel(BaseModel):
    text: str
    previous_dhid: Optional[UUID] = None
    

class ResponseModel(BaseModel):
    reply: str
    now_dhid: Optional[UUID] = None


@router.post("/ask", response_model=ResponseWrapper[ResponseModel])
async def ask(
    data: RequestModel, session_id: UUID = Depends(get_session_id)
) -> ResponseWrapper[ResponseModel]:

    try:
        #当前句子
        sentence_text = data.text
        previous_dhid = data.previous_dhid
        round_id = 0

        openai_account_email = None
        openai_previous_convo_id = None
        openai_conversation_id = None

        assert len(sentence_text) > 0, "need len(sentence_text) > 0"

        # 获取所有历史信息
        last_dialog_info = await get_now_dialog_info(
            session_id=session_id,
            dhid=previous_dhid
        )

        if last_dialog_info is not None:
            previous_dhid = last_dialog_info.dhid
            round_id = last_dialog_info.round_id + 1

            openai_account_email = last_dialog_info.openai_account_email
            openai_previous_convo_id = last_dialog_info.openai_previous_convo_id
            openai_conversation_id = last_dialog_info.openai_conversation_id

        now_dhid = uuid1()

        chatgpt_client = get_chatgpt_client()

        answer = ""
        new_openai_account_email = ""
        new_openai_previous_convo_id = ""
        new_openai_conversation_id = ""

        async for chatgpt_result in chatgpt_client.ask(
            prompt=sentence_text,
            account_email=openai_account_email,
            previous_convo_id=openai_previous_convo_id,
            conversation_id=openai_conversation_id,
        ):
            answer = chatgpt_result[0]
            new_openai_account_email = chatgpt_result[1]
            new_openai_previous_convo_id = chatgpt_result[2]
            new_openai_conversation_id = chatgpt_result[3]

        # 保存最后一轮
        await save_new_dialog_info_and_update_now(
            session_id=session_id,
            round_id=round_id,

            ask_text=sentence_text,
            answer_text=answer,

            dhid=now_dhid,
            previous_dhid=previous_dhid,
            openai_account_email=new_openai_account_email,
            openai_previous_convo_id=new_openai_previous_convo_id,
            openai_conversation_id=new_openai_conversation_id,
        )
        return ResponseWrapper(
            code=ResponseCode.success,
            result=ResponseModel.parse_obj(dict(
                reply=answer,
                now_dhid=now_dhid,
            )),
        )
    except:
        error_text = traceback.format_exc()
        logger.warning("Error:\n" + error_text)
        return ResponseWrapper(
            code=ResponseCode.internal_error,
            result=ResponseModel.parse_obj(dict(
                reply=error_text,
                now_dhid=None,
            )),
        )



@router.post("/ask_streaming")
async def ask_streaming(
    data: RequestModel, session_id: UUID = Depends(get_session_id)
) -> Union[StreamingResponse, ResponseWrapper[ResponseModel]]:
    try:
        #当前句子
        sentence_text = data.text
        previous_dhid = data.previous_dhid
        round_id = 0

        openai_account_email = None
        openai_previous_convo_id = None
        openai_conversation_id = None

        assert len(sentence_text) > 0, "need len(sentence_text) > 0"

        # 获取所有历史信息
        last_dialog_info = await get_now_dialog_info(
            session_id=session_id,
            dhid=previous_dhid
        )

        if last_dialog_info is not None:
            previous_dhid = last_dialog_info.dhid
            round_id = last_dialog_info.round_id + 1

            openai_account_email = last_dialog_info.openai_account_email
            openai_previous_convo_id = last_dialog_info.openai_previous_convo_id
            openai_conversation_id = last_dialog_info.openai_conversation_id

        # 手动尝试第一次迭代
        now_dhid = uuid1()

        chatgpt_client = get_chatgpt_client()

        r_iter = chatgpt_client.ask(
            prompt=sentence_text,
            account_email=openai_account_email,
            previous_convo_id=openai_previous_convo_id,
            conversation_id=openai_conversation_id,
        )

        answer, new_openai_account_email, new_openai_previous_convo_id, new_openai_conversation_id = await r_iter.__anext__()
            
        # 重新封装返回器
        async def response_generator():
            nonlocal answer
            nonlocal new_openai_account_email
            nonlocal new_openai_previous_convo_id
            nonlocal new_openai_conversation_id

            try:
                while True:
                    yield (b"data: " + json.dumps(dict(
                        reply=answer,
                        now_dhid=str(now_dhid)
                    ), ensure_ascii=False).encode("utf8") + b"\n")

                    answer, new_openai_account_email, new_openai_previous_convo_id, new_openai_conversation_id = await r_iter.__anext__()

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
                openai_account_email=new_openai_account_email,
                openai_previous_convo_id=new_openai_previous_convo_id,
                openai_conversation_id=new_openai_conversation_id,
            )

            yield b"data: [DONE]\n"

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
