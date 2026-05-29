from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    total: int | None = None
    cursor: str | None = None
    has_next: bool = False


class Response(BaseModel, Generic[T]):
    data: T
    meta: Meta | None = None


class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: Meta


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    errors: list[ErrorDetail] | None = None
