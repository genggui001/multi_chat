import asyncio
import json
import os
import random
from typing import AsyncGenerator, List, Mapping, Optional, Tuple

import aiofiles
from asyncer import asyncify
from multi_chat.redis import (AvailableOpenAIAccountSet, OpenAIAccount,
                              OpenAIAccountCache)
from pychatgpt.classes import openai
from self_limiters import MaxSleepExceededError, RedisError, Semaphore

from multi_chat import config, logger

from .ask import ask as chatgpt_ask


# 手动转异步
@asyncify
def _openai_login(email:str, password:str, proxy:Optional[str]=None):
    # 删除历史数据
    path = os.path.dirname(os.path.abspath(openai.__file__))
    path = os.path.join(path, "auth.json")
    if os.path.exists(path):
        os.remove(path)

    openai_auth = openai.Auth(email_address=email, password=password, proxy=proxy) # type: ignore
    openai_auth.create_token()

    access_token, expires_at = openai.get_access_token()
    expires_at = int(expires_at) if expires_at is not None else None

    assert type(access_token) == str and len(access_token) > 0

    return access_token, expires_at 


class MChatGPT:
    
    def __init__(self) -> None:
        self.account_map_idx:Mapping[str,int] = {}
        self.accounts:List[OpenAIAccount] = []

        with open(config.model.account_path, "r", encoding="utf-8") as f:
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

        async with aiofiles.open(config.model.account_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(tmp_accounts, indent=4, ensure_ascii=False))


    async def _refresh_all_accounts(self) -> None:
        for account in self.accounts:
            try:
                # 尝试登录更新
                test_re = "fail", "fail", "fail", "fail"
                async for tmp_re in self.ask(
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
            if await AvailableOpenAIAccountSet.exists(item=email) == True:
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
                access_token, expiry = await _openai_login(account.email, account.password, account.proxy)
                account.access_token = access_token
                account.expiry = expiry

                await OpenAIAccountCache.set(key=email, value=account, ex=random.randint(21600, 28800))

                # 设置为
                await AvailableOpenAIAccountSet.add(item=email)

                logger.info(email + " update token")
                return account.access_token, account.expiry, account.proxy

        # 锁拿不到
        except MaxSleepExceededError  as e:
            logger.info(email + "get update lock retry")
            if retry > 0:
                return await self._get_account_access_token(email, refresh_not_available, retry-1)
            else:
                raise Exception(email + "get update lock retry max")

        # redis炸
        except RedisError as e:
            raise e

        except Exception as e:
            if refresh_not_available == False or retry <= 0:
                # 删除账号
                logger.info(email + " is not available")
                
                await AvailableOpenAIAccountSet.remove(item=email)
                raise e
            else:
                logger.info(email + "get update retry")
                return await self._get_account_access_token(email, refresh_not_available, retry-1)

    async def ask(
        self, 
        prompt: str,
        account_email: Optional[str] = None,
        conversation_id: Optional[str] = None,
        previous_convo_id: Optional[str] = None,
        retry: int = 5,
    ) -> AsyncGenerator[Tuple[str, str, str, str], None]:

        if account_email is None:
            account_email = await AvailableOpenAIAccountSet.random_get()

        assert account_email is not None

        try:
            access_token, expiry, proxy = await self._get_account_access_token(account_email, refresh_not_available=True)

            async with Semaphore(
                name="mchatgpt:account_semaphores:" + account_email,
                capacity=10,
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

                async for answer, previous_convo, convo_id in chatgpt_ask(
                    auth_token=(access_token, expiry),
                    prompt=prompt,
                    conversation_id=conversation_id, # type: ignore
                    previous_convo_id=previous_convo_id, # type: ignore
                    proxies=proxy, # type: ignore
                ):
                    yield answer, account_email, previous_convo, convo_id

        except Exception as e:
            e_str =  str(e)
            if (
                "parse your authentication token" in e_str
                or "token has expired" in e_str
            ):
                logger.warning(account_email + "is not available")
                # token 失效注销
                await AvailableOpenAIAccountSet.remove(item=account_email)

                if retry > 0:
                    async for retry_re in self.ask(
                        prompt=prompt,
                        account_email=account_email,
                        conversation_id=conversation_id,
                        previous_convo_id=previous_convo_id,
                        retry=retry,
                    ):
                        yield retry_re
                else:
                    logger.warning(account_email + " retry max")
                    raise e
            elif (
                "Maybe try me again" in e_str
            ):
                if retry > 0:
                    # 休眠一下
                    await asyncio.sleep(0.3)

                    async for retry_re in self.ask(
                        prompt=prompt,
                        account_email=account_email,
                        conversation_id=conversation_id,
                        previous_convo_id=previous_convo_id,
                        retry=retry,
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







