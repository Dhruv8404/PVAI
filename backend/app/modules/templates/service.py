import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ValidationException
from app.modules.templates.model import DocumentTemplate
from app.modules.templates.repository import template_repository
from app.modules.templates.schema import TemplateCreate, TemplateUpdate


class TemplateService:
    async def list_templates(
        self, db: AsyncSession, *, active_only: bool = True
    ) -> List[DocumentTemplate]:
        if active_only:
            stmt = select(DocumentTemplate).where(DocumentTemplate.status == "Active")
            result = await db.execute(stmt)
            return list(result.scalars().all())
        return await template_repository.get_multi(db)

    async def get_template(self, db: AsyncSession, template_id: uuid.UUID) -> DocumentTemplate:
        tpl = await template_repository.get(db, template_id)
        if not tpl:
            raise NotFoundException("Document template not found")
        return tpl

    async def create_template(self, db: AsyncSession, tpl_in: TemplateCreate) -> DocumentTemplate:
        existing = await template_repository.get_by_name(db, tpl_in.name)
        if existing:
            raise ValidationException("A template with this name already exists")
        return await template_repository.create_template(db, obj_in=tpl_in)

    async def update_template(
        self, db: AsyncSession, template_id: uuid.UUID, tpl_in: TemplateUpdate
    ) -> DocumentTemplate:
        tpl = await template_repository.get(db, template_id)
        if not tpl:
            raise NotFoundException("Document template not found")
        return await template_repository.update_template(db, db_obj=tpl, obj_in=tpl_in)

    async def delete_template(self, db: AsyncSession, template_id: uuid.UUID) -> DocumentTemplate:
        tpl = await template_repository.get(db, template_id)
        if not tpl:
            raise NotFoundException("Document template not found")
        return await template_repository.remove(db, id=template_id)


template_service = TemplateService()
