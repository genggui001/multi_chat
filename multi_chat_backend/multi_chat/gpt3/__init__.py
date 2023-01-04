import asyncio
import json
import random
from typing import AsyncGenerator, List, Mapping, Optional, Tuple
from uuid import UUID, uuid1

from multi_chat import config, logger

from .ask import ask as gpt3_ask
from .gpt3_dialog_info import (get_now_dialog_info,
                               save_new_dialog_info_and_update_now)
from .models import OpenAIAccount


class MGPT3:
    
    def __init__(self) -> None:
        self.account_map_idx:Mapping[str,int] = {}
        self.accounts:List[OpenAIAccount] = []

        with open(config.gpt3.account_path, "r", encoding="utf-8") as f:
            tmp_accounts = json.load(f)
            for account_idx, account in enumerate(tmp_accounts):
                self.account_map_idx[account['email']] = account_idx
                self.accounts.append(OpenAIAccount.parse_obj(account))


    async def ask(
        self, 
        prompt: str,
        session_id: UUID,
        previous_dhid: Optional[UUID] = None,
        retry: int = 5,
    ) -> AsyncGenerator[Tuple[str, UUID, UUID], None]:

        openai_account_email = None
        pre_text = None

        # 获取openai历史信息
        last_dialog_info = await get_now_dialog_info(
            session_id=session_id,
            dhid=previous_dhid
        )

        if last_dialog_info is not None:
            openai_account_email = last_dialog_info.openai_account_email
            pre_text = last_dialog_info.pre_text

        # access_token 处理
        if openai_account_email is None:
            openai_account_email = self.accounts[random.randrange(0, len(self.accounts))].email

        assert openai_account_email is not None
        access_token = self.accounts[self.account_map_idx[openai_account_email]].access_token

        try:

            if pre_text is None:
                pre_text = "I am a highly intelligent question answering bot. If you ask me a question that is rooted in truth, I will give you the answer. \nExample:\nQ: Who are you?\nA: Hello! I am Assistant, a large language model trained by OpenAI. I am not a real person, but a computer program designed to assist with answering questions and providing information on a wide range of topics. Is there something specific you'd like to know?"

            ask_prompt = pre_text + "\n\nQ: " + prompt + "\nA: "

            now_dhid = uuid1()
            answer = ""

            async for r_item in gpt3_ask(
                auth_token=access_token,
                prompt=ask_prompt,

            ):
                answer = r_item
                yield answer, session_id, now_dhid 

            if len(answer) > 0:
                await save_new_dialog_info_and_update_now(
                    session_id=session_id,
                    dhid=now_dhid,
                    openai_account_email=openai_account_email,
                    pre_text=(ask_prompt+answer)
                )


        except Exception as e:
            e_str =  str(e)
            if (
                "Maybe try me again" in e_str
                or "incomplete chunked read" in e_str
                or "peer closed connection" in e_str
            ):
                if retry > 0:
                    # 休眠一下
                    await asyncio.sleep(0.3)

                    async for retry_re in self.ask(
                        prompt=prompt,
                        session_id=session_id,
                        previous_dhid=previous_dhid,
                        retry=retry-1,
                    ):
                        yield retry_re
                else:
                    logger.warning(openai_account_email + " retry max")
                    raise e
            else:
                raise e

_gpt3_client: Optional[MGPT3] = None

async def create_gpt3_client():
    global _gpt3_client
    _gpt3_client = MGPT3()



def get_gpt3_client() -> MGPT3:
    if _gpt3_client is None:
        raise ValueError("gpt3 client connection has not been initialized.")
    return _gpt3_client