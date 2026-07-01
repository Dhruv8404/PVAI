import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.repository import BaseRepository
from app.modules.templates.model import DocumentTemplate
from app.modules.templates.schema import TemplateCreate, TemplateUpdate


class TemplateRepository(BaseRepository[DocumentTemplate]):
    def __init__(self):
        super().__init__(DocumentTemplate)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[DocumentTemplate]:
        stmt = select(DocumentTemplate).where(DocumentTemplate.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_template(self, db: AsyncSession, *, obj_in: TemplateCreate) -> DocumentTemplate:
        obj_in_data = obj_in.model_dump()
        return await self.create(db, obj_in_data=obj_in_data)

    async def update_template(
        self, db: AsyncSession, *, db_obj: DocumentTemplate, obj_in: TemplateUpdate
    ) -> DocumentTemplate:
        obj_in_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in_data=obj_in_data)


template_repository = TemplateRepository()
