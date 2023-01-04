import asyncio
import json
import random
import traceback
from typing import Optional

import httpx
from pydantic import BaseModel, BaseSettings, Field
from self_limiters import MaxSleepExceededError, RedisError, Semaphore

from multi_chat import config, logger

from ..redis import RedisCache


class CFClearance(BaseModel):
    success: bool
    msg: str
    user_agent: str
    cookies: dict

class CFClearanceCache(RedisCache[CFClearance]):
    pass
    

    
async def get_cf_clearance(
    url: str, 
    proxies: Optional[str] = None,
    retry: int=5
) -> CFClearance:
    
    # 写缓存模式
    cf_clearance = await CFClearanceCache.get(key=url+str(proxies))

    if cf_clearance is not None:
        return cf_clearance

    # if proxies is not None:
    #     if isinstance(proxies, str):
    #         proxies = {'http': proxies, 'https': proxies} # type: ignore

    try:
        # 获取锁
        async with Semaphore(
            name="mchatgpt:get_cf_clearance_lock_" + url + str(proxies),
            capacity=1,
            redis_url=config.redis.redis_url,
            expiry=1800,
            max_sleep=1.0,
        ):

            async with httpx.AsyncClient() as session: # type: ignore
                cf_clearance_res = await session.post(
                    url=config.chatgpt.get_cf_clearance_url,
                    headers = {
                        'Content-Type': 'application/json',
                    },
                    data=json.dumps({
                        "proxy": {"server": "" if proxies is None else proxies} , 
                        "timeout": 60, 
                        "url": url
                    }),  # type: ignore
                    timeout=120,
                )

                cf_clearance_res = CFClearance.parse_obj(cf_clearance_res.json())

                assert "cf_clearance" in cf_clearance_res.cookies

                await CFClearanceCache.set(key=url+str(proxies), value=cf_clearance_res, ex=random.randint(3600, 5400))

                logger.info(url + " cf clearance")
                return cf_clearance_res


    # 锁拿不到
    except MaxSleepExceededError  as e:
        logger.info(url + " get update lock retry")
        if retry > 0:
            await asyncio.sleep(1)
            return await get_cf_clearance(url=url, retry=retry-1, proxies=proxies)
        else:
            raise Exception(url + " get update lock retry max")

    # redis炸
    except RedisError as e:
        raise e

    except Exception as e:
        if  retry <= 0:
            # 删除账号
            logger.info(url + " is not available")
            raise e
        else:
            logger.info(url + " cf clearance update retry")
            logger.warning(traceback.format_exc())
            await asyncio.sleep(1)
            return await get_cf_clearance(url=url, retry=retry-1, proxies=proxies)




