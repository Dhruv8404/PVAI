from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import RoleRequirement
from app.modules.dashboard.schema import DashboardFullResponse
from app.modules.dashboard.service import dashboard_service
from app.modules.auth.schema import ApiResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])

from app.core.dependencies import get_current_user
from app.modules.users.model import User


@router.get("", response_model=ApiResponse[DashboardFullResponse])
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    data = await dashboard_service.get_dashboard_data(db, current_user)
    return ApiResponse(
        success=True,
        message="Fetched dashboard details successfully",
        data=data
    )
