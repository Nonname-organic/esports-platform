import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """汎用CRUDリポジトリ。全リポジトリの基底クラス。"""

    def __init__(self, model: type[ModelT], db: AsyncSession):
        self._model = model
        self._db = db

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        result = await self._db.execute(
            select(self._model).where(self._model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *filters: Any,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ModelT]:
        stmt = select(self._model).where(*filters).limit(limit).offset(offset)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *filters: Any) -> int:
        stmt = select(func.count()).select_from(self._model).where(*filters)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self._model(**kwargs)
        self._db.add(instance)
        await self._db.flush()
        await self._db.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        for key, value in kwargs.items():
            if value is not None:
                setattr(instance, key, value)
        await self._db.flush()
        await self._db.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self._db.delete(instance)
        await self._db.flush()

    async def save(self, instance: ModelT) -> ModelT:
        self._db.add(instance)
        await self._db.flush()
        await self._db.refresh(instance)
        return instance
