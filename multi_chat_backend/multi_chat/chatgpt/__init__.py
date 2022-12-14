import asyncio
import json
import os
import random
from typing import AsyncGenerator, List, Mapping, Optional, Tuple
from uuid import UUID, uuid1

import aiofiles
from asyncer import asyncify
from pychatgpt.classes import exceptions as Exceptions
from self_limiters import MaxSleepExceededError, RedisError, Semaphore

from multi_chat import config, logger

from . import auth as openai
from .ask import ask as chatgpt_ask
from .available_openai_account_set import (AvailableOpenAIAccount,
                                           AvailableOpenAIAccountSet)
from .cf_clearance import CFClearance, CFClearanceCache, get_cf_clearance
from .chatgpt_dialog_info import (get_now_dialog_info,
                                  save_new_dialog_info_and_update_now)
from .openai_account_cache import OpenAIAccount, OpenAIAccountCache


# 手动转异步
@asyncify
def _openai_login(
    email:str, 
    password:str, 
    proxy:Optional[str]=None,
    chat_cf_clearance: Optional[CFClearance]=None,
):
    # 删除历史数据
    path = os.path.dirname(os.path.abspath(openai.__file__))
    path = os.path.join(path, "auth.json")
    if os.path.exists(path):
        os.remove(path)

    openai_auth = openai.Auth(
        email_address=email, 
        password=password, 
        proxy=proxy,
        user_agent=chat_cf_clearance.user_agent if chat_cf_clearance is not None else None,
        cookies=chat_cf_clearance.cookies if chat_cf_clearance is not None else None,
    ) # type: ignore
    access_token, expires_at = openai_auth.create_token() # type: ignore

    expires_at = int(expires_at) if expires_at is not None else None

    assert type(access_token) == str and len(access_token) > 0

    return access_token, expires_at 


class MChatGPT:
    
    def __init__(self) -> None:
        self.account_map_idx:Mapping[str,int] = {}
        self.accounts:List[OpenAIAccount] = []

        with open(config.chatgpt.account_path, "r", encoding="utf-8") as f:
            tmp_accounts = json.load(f)
            for account_idx, account in enumerate(tmp_accounts):
                self.account_map_idx[account['email']] = account_idx
                self.accounts.append(OpenAIAccount.parse_obj(account))


    async def _save_accounts_to_json(self) -> None:
        tmp_accounts = []
        for account in self.accounts:
            new_account = await OpenAIAccountCache.get(account.email)
            # 获取数据失败
            if new_account is None:
                new_account = account

            tmp_accounts.append(new_account.dict())

        async with aiofiles.open(config.chatgpt.account_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(tmp_accounts, indent=4, ensure_ascii=False))


    async def _refresh_all_accounts(self) -> None:
        for account in self.accounts:
            try:
                # 尝试登录更新
                test_re = "fail", "fail", "fail", "fail"
                async for tmp_re in self._ask(
                    prompt="1+1=?",
                    account_email=account.email,
                    conversation_id=None,
                    previous_convo_id=None,
                ):
                    test_re = tmp_re
                logger.info(account.email + " login success")
                logger.info("answer is: " + test_re[0])
            except Exception as e:
                logger.info(account.email + " login fail")
                logger.exception(e)

        # 检查
        assert await AvailableOpenAIAccountSet.count() > 0, "至少一个可用账号"
        # 保存
        await self._save_accounts_to_json()

        logger.info("refresh all accounts finish")

    async def _get_account_access_token(
        self, 
        email: str, 
        refresh_not_available: bool=False, 
        retry: int=5
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        
        # 写缓存模式
        account = await OpenAIAccountCache.get(key=email)

        if account is not None:
            if await AvailableOpenAIAccountSet.exists(item=AvailableOpenAIAccount(email=email)) == True:
                return account.access_token, account.expiry, account.proxy
            else:
                logger.info(email + " is not available")
                if refresh_not_available == False:
                    raise Exception("account is not available")

        try:
            # 获取锁
            async with Semaphore(
                name="mchatgpt:account_cache_update_lock",
                capacity=1,
                redis_url=config.redis.redis_url,
                expiry=1800,
                max_sleep=1.0,
            ):
                account = self.accounts[self.account_map_idx[email]]

                chat_cf_clearance = await get_cf_clearance(
                    url="https://chat.openai.com/chat",
                    proxies=account.proxy
                )

                # auth0_cf_clearance = await get_cf_clearance(
                #     url="https://auth0.openai.com/",
                #     proxies=account.proxy
                # )

                access_token, expiry = await _openai_login(
                    email=account.email, 
                    password=account.password, 
                    proxy=account.proxy,
                    chat_cf_clearance=chat_cf_clearance,
                )
                account.access_token = access_token
                account.expiry = expiry

                await OpenAIAccountCache.set(key=email, value=account, ex=random.randint(21600, 28800))

                # 设置为
                await AvailableOpenAIAccountSet.add(item=AvailableOpenAIAccount(email=email))

                logger.info(email + " update token")
                return account.access_token, account.expiry, account.proxy

        # 锁拿不到
        except MaxSleepExceededError  as e:
            logger.info(email + "get update lock retry")
            if retry > 0:
                return await self._get_account_access_token(email, refresh_not_available, retry-1)
            else:
                raise Exception(email + "get update lock retry max")

        except Exceptions.Auth0Exception as e:
            # cf 失效
            logger.warning("https://chat.openai.com/chat cf is not available")
            await CFClearanceCache.delete(key="https://chat.openai.com/chat")
            raise e

        # redis炸
        except RedisError as e:
            raise e

        except Exception as e:
            if refresh_not_available == False or retry <= 0:
                # 删除账号
                logger.info(email + " is not available")
                
                await AvailableOpenAIAccountSet.remove(item=AvailableOpenAIAccount(email=email))
                raise e
            else:
                logger.info(email + "get update retry")
                return await self._get_account_access_token(email, refresh_not_available, retry-1)


    async def ask(
        self, 
        prompt: str,
        session_id: UUID,
        previous_dhid: Optional[UUID] = None,
        retry: int = 5,
    ) -> AsyncGenerator[Tuple[str, UUID, UUID], None]:

        openai_account_email = None
        openai_previous_convo_id = None
        openai_conversation_id = None

        # 获取openai历史信息
        last_dialog_info = await get_now_dialog_info(
            session_id=session_id,
            dhid=previous_dhid
        )

        if last_dialog_info is not None:
            openai_account_email = last_dialog_info.openai_account_email
            openai_previous_convo_id = last_dialog_info.openai_previous_convo_id
            openai_conversation_id = last_dialog_info.openai_conversation_id

        now_dhid = uuid1()

        answer = ""
        new_openai_account_email = ""
        new_openai_previous_convo_id = ""
        new_openai_conversation_id = ""

        async for r_item in self._ask(
            prompt=prompt,
            account_email=openai_account_email,
            previous_convo_id=openai_previous_convo_id,
            conversation_id=openai_conversation_id,
            retry=retry,
        ):
            answer = r_item[0]
            new_openai_account_email = r_item[1]
            new_openai_previous_convo_id = r_item[2]
            new_openai_conversation_id = r_item[3]
            
            yield answer, session_id, now_dhid 

        if len(answer) > 0:
            await save_new_dialog_info_and_update_now(
                session_id=session_id,

                dhid=now_dhid,
                openai_account_email=new_openai_account_email,
                openai_previous_convo_id=new_openai_previous_convo_id,
                openai_conversation_id=new_openai_conversation_id,
            )


    async def _ask(
        self, 
        prompt: str,
        account_email: Optional[str] = None,
        conversation_id: Optional[str] = None,
        previous_convo_id: Optional[str] = None,
        retry: int = 5,
    ) -> AsyncGenerator[Tuple[str, str, str, str], None]:

        if account_email is None:
            tmp_account_email = await AvailableOpenAIAccountSet.random_get()
            account_email = tmp_account_email.email if tmp_account_email is not None else None

        assert account_email is not None

        try:
            access_token, expiry, proxy = await self._get_account_access_token(account_email, refresh_not_available=True)

            async with Semaphore(
                name="mchatgpt:account_semaphores:" + account_email,
                capacity=1,
                redis_url=config.redis.redis_url,
                expiry=1800,
                max_sleep=5.0,
            ):

                logger.info(
                    "Request: \n" + 
                    json.dumps(dict(
                        account_email=account_email,
                        prompt=prompt,
                        conversation_id=conversation_id, # type: ignore
                        previous_convo_id=previous_convo_id, # type: ignore
                        proxies=proxy, # type: ignore
                    ), indent=4, ensure_ascii=False)
                )

                chat_cf_clearance = await get_cf_clearance(
                    url="https://chat.openai.com/chat",
                    proxies=proxy
                )

                async for answer, previous_convo, convo_id in chatgpt_ask(
                    auth_token=(access_token, expiry),
                    prompt=prompt,
                    conversation_id=conversation_id, # type: ignore
                    previous_convo_id=previous_convo_id, # type: ignore
                    proxies=proxy, # type: ignore
                    chat_cf_clearance=chat_cf_clearance,
                ):
                    yield answer, account_email, previous_convo, convo_id

        except Exception as e:
            e_str =  str(e)
            if (
                "parse your authentication token" in e_str
                or "token has expired" in e_str
                or "Too many requests in 1 hour" in e_str
            ):
                logger.warning(account_email + "\n" + e_str)
                # logger.warning(account_email + " is not available")
                # token 失效注销
                await AvailableOpenAIAccountSet.remove(item=AvailableOpenAIAccount(email=account_email))

                if retry > 0:
                    async for retry_re in self._ask(
                        prompt=prompt,
                        account_email=account_email,
                        conversation_id=conversation_id,
                        previous_convo_id=previous_convo_id,
                        retry=retry-1,
                    ):
                        yield retry_re
                else:
                    logger.warning(account_email + " retry max")
                    raise e
            elif (
                "Maybe try me again" in e_str
                or "incomplete chunked read" in e_str
                or "peer closed connection" in e_str
            ):
                if retry > 0:
                    # 休眠一下
                    await asyncio.sleep(0.3)

                    async for retry_re in self._ask(
                        prompt=prompt,
                        account_email=account_email,
                        conversation_id=conversation_id,
                        previous_convo_id=previous_convo_id,
                        retry=retry-1,
                    ):
                        yield retry_re
                else:
                    logger.warning(account_email + " retry max")
                    raise e
            elif (
                "[Status Code] 403" in e_str 
                and "cloudflare" in e_str 
            ):
                if retry > 0:
                    
                    # 休眠一下
                    await asyncio.sleep(0.3)
                    logger.warning("https://chat.openai.com/chat" + " cf is not available")
                    await CFClearanceCache.delete(key="https://chat.openai.com/chat")

                    async for retry_re in self._ask(
                        prompt=prompt,
                        account_email=account_email,
                        conversation_id=conversation_id,
                        previous_convo_id=previous_convo_id,
                        retry=retry-1,
                    ):
                        yield retry_re
                else:
                    logger.warning(account_email + " retry max")
                    raise e
            else:
                raise e

    
_chatgpt_client: Optional[MChatGPT] = None

async def create_chatgpt_client():
    global _chatgpt_client
    _chatgpt_client = MChatGPT()

    await _chatgpt_client._refresh_all_accounts()


def get_chatgpt_client() -> MChatGPT:
    if _chatgpt_client is None:
        raise ValueError("chatgpt client connection has not been initialized.")
    return _chatgpt_client







