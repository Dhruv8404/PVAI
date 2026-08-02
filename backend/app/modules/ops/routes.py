import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.task_queue import get_worker_status
from app.core.cache_service import cache_service
from app.core.dr_validator import run_dr_validation
from app.core.feature_flags import feature_flags
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops", tags=["Operational Diagnostics Dashboard"])


@router.get("/diagnostics", status_code=status.HTTP_200_OK)
async def get_ops_diagnostics(db: AsyncSession = Depends(get_db)):
    """Exposes administrative diagnostics detailing workers, cache, disaster recovery, and features."""
    logger.info("[OPS] Generating operational diagnostics report...")
    
    # 1. Background worker & queues status
    worker_info = get_worker_status()
    
    # 2. Caching statistics
    cache_info = cache_service.get_stats()
    
    # 3. Feature Flags status
    flags_info = feature_flags.get_all_flags()
    
    # 4. Disaster Recovery validation
    dr_info = await run_dr_validation()
    
    # 5. Active LLM configurations
    active_providers = [settings.LLM_PROVIDER]
    
    report = {
        "status": "healthy" if dr_info.get("status") == "READY" else "degraded",
        "active_ai_providers": active_providers,
        "feature_flags": flags_info,
        "cache": cache_info,
        "worker": worker_info,
        "disaster_recovery": dr_info
    }
    
    return report
