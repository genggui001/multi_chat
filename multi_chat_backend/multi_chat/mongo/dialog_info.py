import time
from typing import Optional
from uuid import UUID, uuid1

from multi_chat.mongo import DialogHistory
from multi_chat.redis import DialogStateCache


async def get_one_dialog_info(
    session_id: UUID,
    dhid: UUID,
) -> Optional[DialogHistory]:
    """获取从开始到当前轮所有的对话信息 接口文档5.1

    Param:
        session_id: 某一次对话的标记会话id

    Return:
        该对话的所有轮次对话信息
    """
    return await DialogHistory.get(dhid=dhid, session_id=session_id)


async def get_now_dialog_info(
    session_id: UUID,
    dhid: Optional[UUID] = None,
) -> Optional[DialogHistory]:

    now_state = await DialogStateCache.get(key=str(session_id))

    if dhid is None:
        # dhid is None 默认找最近的一次
        if now_state is None:
            return None
        else:
            return now_state
    else:
        if now_state is not None and dhid == now_state.dhid:
            return now_state
        else:
            return await get_one_dialog_info(session_id=session_id, dhid=dhid)


async def save_new_dialog_info_and_update_now(
    session_id: UUID,
    round_id: int,

    ask_text: str,
    answer_text: str,

    dhid: Optional[UUID] = None,
    previous_dhid: Optional[UUID] = None,
    openai_account_email: Optional[str] = None,
    openai_conversation_id: Optional[str] = None,
    openai_previous_convo_id: Optional[str] = None,
) -> DialogHistory:
    """存储新一轮的患者或系统的对话信息 接口文档5.2

    Param:
        dialog_history_unit: 存储对话记录的单元(包含round_id, speaker, sentence_text和analysis_result)

    Return:
        存储结果提示
    """
    if dhid is None:
        dhid = uuid1()
        
    answer_timestamp = int(time.time())

    new_dialog_info = await DialogHistory.new(
        dhid=dhid,
        previous_dhid=previous_dhid,

        session_id=session_id,
        round_id=round_id,

        ask_text=ask_text,
        answer_text=answer_text,
        answer_timestamp=answer_timestamp,

        openai_account_email=openai_account_email,
        openai_conversation_id=openai_conversation_id,
        openai_previous_convo_id=openai_previous_convo_id,
    )

    # 允许存活时间10分钟
    await DialogStateCache.set(key=str(session_id), value=new_dialog_info, ex=600)

    return new_dialog_info

