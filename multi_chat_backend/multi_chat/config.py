from typing import List, Literal, Optional

from pydantic import BaseModel, BaseSettings, Field


class Oauth2Config(BaseModel):
    secret_key: str = 'bfaa7abddeb09e429c760a323734c797689cd8a7ea6368bb15ccf3bc941e9aa5'
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

class UvicornConfig(BaseModel):
    app_module: str = "multi_chat:app"
    host: str = "127.0.0.1"
    port: int = 59815
    reload: bool = False


class FastAPIConfig(BaseModel):
    debug: bool = False
    openapi_url: Optional[str] = None
    docs_url: Optional[str] = None
    redoc_url: Optional[str] = None


class MongoConfig(BaseModel):
    mongo_url: str = "mongodb://localhost:27017"
    mongo_database: str = "multi_chat"

class RedisConfig(BaseModel):
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "multi_chat"


class ChatGPTConfig(BaseModel):
    account_path: str = "./accounts/chatgpt.json"
    refresh_passwd: str = "Tiankong1234"
    refresh_seconds: int = 3600
    get_cf_clearance_url : str = "http://127.0.0.1:8000/challenge"


class GPT3Config(BaseModel):
    account_path: str = "./accounts/gpt3.json"


class SinkConfig(BaseModel):
    type: Literal["file", "stdout", "stderr"] = "stdout"
    filename: str = "{time}.log"


class LoggerConfig(BaseModel):
    sink: SinkConfig = Field(default_factory=SinkConfig)
    level: str = "INFO"
    colorize: Optional[bool] = None
    diagnose: bool = False


class Config(BaseSettings):
    uvicorn: UvicornConfig = Field(default_factory=UvicornConfig)
    oauth2: Oauth2Config = Field(default_factory=Oauth2Config)
    fastapi: FastAPIConfig = Field(default_factory=FastAPIConfig)
    mongo: MongoConfig = Field(default_factory=MongoConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    chatgpt: ChatGPTConfig = Field(default_factory=ChatGPTConfig)
    gpt3: GPT3Config = Field(default_factory=GPT3Config)
    logger: List[LoggerConfig] = [LoggerConfig()]

    class Config:
        extra = "allow"
        env_file = ".env"
        env_nested_delimiter = "__"
