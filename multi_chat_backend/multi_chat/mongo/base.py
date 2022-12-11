from typing import Optional, Type, TypeVar
from uuid import UUID

from bson import ObjectId
from bson.errors import InvalidId
from motor.core import AgnosticCollection, AgnosticCursor
from pydantic import BaseModel, Field

from . import get_database

T = TypeVar("T", bound="MongoModel")


class OID(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            return cls(str(v))
        except InvalidId:
            raise ValueError("Not a valid ObjectId") from None


class MongoModel(BaseModel):
    id: OID = Field(alias="_id")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: lambda x: str(x), UUID: lambda x: str(x)}

    def dict(self, **kwargs) -> dict:
        kwargs.pop("by_alias", None)
        return super().dict(by_alias=True, **kwargs)

    @classmethod
    def collection_name(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def collection(cls) -> AgnosticCollection:
        return get_database()[cls.collection_name()]

    @classmethod
    async def get(cls: Type[T], **kwargs) -> Optional[T]:
        obj: T = await cls.collection().find_one(kwargs)  # type: ignore
        return cls.parse_obj(obj) if obj else None

    @classmethod
    async def list(
        cls: Type[T], sort: Optional[str] = None, length: int = 100, **kwargs
    ) -> list[T]:
        cursor: AgnosticCursor
        if sort:
            cursor = cls.collection().find(kwargs).sort(sort)  # type: ignore
        else:
            cursor = cls.collection().find(kwargs)

        return [cls.parse_obj(x) for x in await cursor.to_list(length=length)]

    async def save(self) -> int:
        result = await self.collection().replace_one(
            {"_id": self.id}, self.dict()
        )  # type: ignore
        return result.modified_count

    async def delete(self) -> int:
        result = await self.collection().delete_many({"_id": self.id})  # type: ignore
        return result.deleted_count

    @classmethod
    async def new(cls: Type[T], **kwargs) -> T:
        await cls.collection().insert_one(kwargs)  # type: ignore
        return cls(**kwargs)
