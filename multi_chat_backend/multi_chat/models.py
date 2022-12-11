from enum import IntEnum
from typing import Generic, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

R = TypeVar("R", bound=BaseModel)


class ResponseCode(IntEnum):
    success = 0
    empty_result = 10
    internal_error = 20


class ResponseWrapper(GenericModel, Generic[R]):
    code: ResponseCode = ResponseCode.success
    result: R


