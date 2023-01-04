from typing import Optional

from motor.core import AgnosticClient, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient

from multi_chat import config

_client: Optional[AgnosticClient] = None
_db: Optional[AgnosticDatabase] = None


async def create_connection():
    global _client, _db
    _client = client = AsyncIOMotorClient(
        config.mongo.mongo_url,
        authSource=config.mongo.mongo_database,
        uuidRepresentation="standard",
    )
    _db = client[config.mongo.mongo_database]


def get_database() -> AgnosticDatabase:
    if _db is None:
        raise ValueError("Database connection has not been initialized.")
    return _db


from .base import OID as OID
from .base import MongoModel as MongoModel
