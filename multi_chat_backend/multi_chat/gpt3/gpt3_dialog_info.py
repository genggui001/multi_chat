import time
from typing import Optional
from uuid import UUID, uuid1

from .gpt3_dialog_state_cache import GPT3DialogStateCache
from .models import GPT3DialogHistory


async def get_one_dialog_info(
    session_id: UUID,
    dhid: UUID,
) -> Optional[GPT3DialogHistory]:
    """获取从开始到当前轮所有的对话信息 接口文档5.1

    Param:
        session_id: 某一次对话的标记会话id

    Return:
        该对话的所有轮次对话信息
    """
    return await GPT3DialogHistory.get(dhid=dhid, session_id=session_id)


async def get_now_dialog_info(
    session_id: UUID,
    dhid: Optional[UUID] = None,
) -> Optional[GPT3DialogHistory]:

    now_state = await GPT3DialogStateCache.get(key=str(session_id))

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
            now_state = await get_one_dialog_info(session_id=session_id, dhid=dhid)
            
            if now_state is not None:
                await GPT3DialogStateCache.set(key=str(session_id), value=now_state, ex=600)

            return now_state


async def save_new_dialog_info_and_update_now(
    session_id: UUID,
    dhid: Optional[UUID] = None,
    openai_account_email: Optional[str] = None,
    pre_text: Optional[str] = None,
) -> GPT3DialogHistory:
    """存储新一轮的患者或系统的对话信息 接口文档5.2

    Param:
        dialog_history_unit: 存储对话记录的单元(包含round_id, speaker, sentence_text和analysis_result)

    Return:
        存储结果提示
    """
    if dhid is None:
        dhid = uuid1()
        
    new_dialog_info = await GPT3DialogHistory.new(
        session_id=session_id,
        dhid=dhid,

        openai_account_email=openai_account_email,
        pre_text=pre_text,
    )

    # 允许存活时间10分钟
    await GPT3DialogStateCache.set(key=str(session_id), value=new_dialog_info, ex=600)

    return new_dialog_info

