import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, session
from .chatgpt import create_chatgpt_client, get_chatgpt_client, refresh
from .dialog import ask, conversation, feedback, moderations
from .gpt3 import create_gpt3_client
from .log import logger
from .mongo import create_connection as create_mongo_connection
from .oauth2 import token
from .redis import create_connection as create_redis_connection
from .tasks import repeat_task

app = FastAPI(
    debug=config.fastapi.debug,
    title="Multi ChatGPT Bot",
    openapi_url=config.fastapi.openapi_url,
    docs_url=config.fastapi.docs_url,
    redoc_url=config.fastapi.redoc_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask.router, prefix="/dialog", tags=["dialog"])
app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(refresh.router, prefix="/refresh", tags=["refresh"])

# 原版接口
app.include_router(conversation.router, prefix="/backend-api", tags=["backend-api"])
app.include_router(feedback.router, prefix="/backend-api", tags=["backend-api"])
app.include_router(moderations.router, prefix="/backend-api", tags=["backend-api"])

# 登录接口
app.include_router(token.router, prefix="/oauth2", tags=["oauth2"])

@app.on_event('startup')
@repeat_task(seconds=config.chatgpt.refresh_seconds, wait_first=True)
async def refresh_chatgpt_all_accounts() -> None:
    logger.info('刷新chatgpt的所有用户')
    await get_chatgpt_client()._refresh_all_accounts()


@app.on_event("startup")
async def startup():

    # 数据连接初始化
    await asyncio.gather(
        create_mongo_connection(),
        create_redis_connection(),
    )

    # chatgpt初始化
    await asyncio.gather(
        create_chatgpt_client(),
        create_gpt3_client(),
    )

    logger.info("startup success")

    