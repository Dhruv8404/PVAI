from typing import Any, Generic, Type, TypeVar, Union
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Union[ModelType, None]:
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in_data: dict) -> ModelType:
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in_data: dict
    ) -> ModelType:
        for field in obj_in_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_in_data[field])
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def remove(self, db: AsyncSession, *, id: Any) -> Union[ModelType, None]:
        db_obj = await self.get(db, id)
        if db_obj:
            await db.delete(db_obj)
            await db.flush()
        return db_obj
