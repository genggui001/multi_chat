from typing import List, Literal, Optional

from pydantic import BaseModel, BaseSettings, Field


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


class ModelConfig(BaseModel):
    account_path: str = "./accounts.json"
    refresh_passwd: str = "Tiankong1234"
    refresh_seconds: int = 600

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
    fastapi: FastAPIConfig = Field(default_factory=FastAPIConfig)
    mongo: MongoConfig = Field(default_factory=MongoConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    logger: List[LoggerConfig] = [LoggerConfig()]

    class Config:
        extra = "allow"
        env_file = ".env"
        env_nested_delimiter = "__"