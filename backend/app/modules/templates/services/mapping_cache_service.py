import logging
import uuid
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.templates.model import CustomerHeaderMapping

logger = logging.getLogger(__name__)


class MappingCacheService:
    async def get_cached_mapping(
        self, 
        db: AsyncSession, 
        customer_id: str, 
        template_id: uuid.UUID, 
        uploaded_header: str
    ) -> Optional[CustomerHeaderMapping]:
        """Checks the cache table for an existing header mapping mapping for this customer."""
        stmt = select(CustomerHeaderMapping).where(
            and_(
                CustomerHeaderMapping.customer_id == customer_id,
                CustomerHeaderMapping.template_id == template_id,
                CustomerHeaderMapping.uploaded_header == uploaded_header.strip()
            )
        )
        res = await db.execute(stmt)
        mapping = res.scalar_one_or_none()
        if mapping:
            logger.info(f"[Cache Hit] Reusing cached mapping for header '{uploaded_header}' -> '{mapping.mapped_field}'")
        return mapping

    async def save_confirmed_mapping(
        self, 
        db: AsyncSession, 
        customer_id: str, 
        template_id: uuid.UUID, 
        uploaded_header: str, 
        mapped_field: str, 
        confidence: float, 
        source: str,
        status: str = "Confirmed"
    ) -> CustomerHeaderMapping:
        """Upserts a mapping record to the cache database table."""
        stmt = select(CustomerHeaderMapping).where(
            and_(
                CustomerHeaderMapping.customer_id == customer_id,
                CustomerHeaderMapping.template_id == template_id,
                CustomerHeaderMapping.uploaded_header == uploaded_header.strip()
            )
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        
        if existing:
            logger.info(f"[Cache Update] Updating mapping cache for header '{uploaded_header}' -> '{mapped_field}' (Status: {status})")
            existing.mapped_field = mapped_field
            existing.confidence = confidence
            existing.mapping_source = source
            existing.status = status
            db_obj = existing
        else:
            logger.info(f"[Cache Save] Creating new mapping cache for header '{uploaded_header}' -> '{mapped_field}' (Status: {status})")
            db_obj = CustomerHeaderMapping(
                customer_id=customer_id,
                template_id=template_id,
                uploaded_header=uploaded_header.strip(),
                mapped_field=mapped_field,
                confidence=confidence,
                mapping_source=source,
                status=status
            )
            db.add(db_obj)
            
        await db.commit()
        return db_obj

    async def get_mapping_history(
        self, 
        db: AsyncSession, 
        template_id: uuid.UUID
    ) -> List[CustomerHeaderMapping]:
        """Retrieves all previous mappings associated with a template."""
        stmt = select(CustomerHeaderMapping).where(CustomerHeaderMapping.template_id == template_id).order_by(CustomerHeaderMapping.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


mapping_cache_service = MappingCacheService()
