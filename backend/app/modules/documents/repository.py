import uuid
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.repository import BaseRepository
from app.modules.documents.model import GeneratedDocument


class DocumentRepository(BaseRepository[GeneratedDocument]):
    def __init__(self):
        super().__init__(GeneratedDocument)

    async def get_by_user(self, db: AsyncSession, user_id: uuid.UUID) -> List[GeneratedDocument]:
        stmt = select(GeneratedDocument).where(GeneratedDocument.user_id == user_id).order_by(GeneratedDocument.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_relations(self, db: AsyncSession) -> List[GeneratedDocument]:
        stmt = select(GeneratedDocument).order_by(GeneratedDocument.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())


document_repository = DocumentRepository()
