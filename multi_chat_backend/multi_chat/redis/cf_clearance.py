import json
import random
from typing import Optional

import httpx
from pydantic import BaseModel, BaseSettings, Field
from self_limiters import MaxSleepExceededError, RedisError, Semaphore

from multi_chat import config, logger

from . import get_database


class CFClearanceModel(BaseModel):
    success: bool
    msg: str
    user_agent: str
    cookies: dict

    

class CFClearanceCache:
    key_prefix = "multi_chat_gpt:cf_clearance"
    value_model = CFClearanceModel

    @classmethod
    def format_key(cls, key: str) -> str:
        return cls.key_prefix + "__" + key

    @classmethod
    async def get(cls, key: str) -> Optional[CFClearanceModel]:
        obj = await get_database().get(cls.format_key(key)) # type: ignore
        return cls.value_model.parse_raw(obj, encoding="utf8") if obj else None
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        return await get_database().exists(cls.format_key(key)) # type: ignore

    @classmethod
    async def set(
        cls, 
        key: str, 
        value: CFClearanceModel,
        ex: Optional[int] = None,
    ):
        await get_database().set(cls.format_key(key), value.json().encode(encoding="utf8"), ex=ex) # type: ignore

    
async def get_cf_clearance(
    url: str, 
    proxies: Optional[str] = None,
    retry: int=5
) -> CFClearanceModel:
    
    # 写缓存模式
    cf_clearance = await CFClearanceCache.get(key=url)

    if cf_clearance is not None:
        return cf_clearance

    try:

        if proxies is not None:
            if isinstance(proxies, str):
                proxies = {'http': proxies, 'https': proxies} # type: ignore

        async with httpx.AsyncClient(proxies=proxies) as session: # type: ignore
            cf_clearance_res = await session.post(
                url=config.model.get_cf_clearance_url,
                headers = {
                    'Content-Type': 'application/json',
                },
                data=json.dumps({
                    "proxy": {"server": "" if proxies is None else proxies} , 
                    "timeout": 30, 
                    "url": url
                }),  # type: ignore
            )

            cf_clearance_res = CFClearanceModel.parse_obj(cf_clearance_res.json())

            assert "cf_clearance" in cf_clearance_res.cookies

            await CFClearanceCache.set(key=url, value=cf_clearance_res, ex=random.randint(64800, 86400))

            logger.info(url + " cf clearance")
            return cf_clearance_res

    # redis炸
    except RedisError as e:
        raise e

    except Exception as e:
        if  retry <= 0:
            # 删除账号
            logger.info(url + " is not available")
            raise e
        else:
            logger.info(url + "cf clearance update retry")
            return await get_cf_clearance(url=url, retry=retry-1)




