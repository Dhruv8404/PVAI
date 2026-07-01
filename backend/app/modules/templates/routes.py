import uuid
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleRequirement
from app.modules.users.model import User
from app.modules.templates.schema import TemplateResponse, TemplateCreate, TemplateUpdate
from app.modules.templates.service import template_service
from app.modules.auth.schema import ApiResponse

router = APIRouter(prefix="/templates", tags=["Templates Management"])

require_admin = RoleRequirement(["Admin"])


@router.get("", response_model=ApiResponse[List[TemplateResponse]])
async def get_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is admin to return inactive templates too
    user_roles_list = [r.name for r in current_user.roles]
    active_only = "Admin" not in user_roles_list

    templates = await template_service.list_templates(db, active_only=active_only)
    response_data = [TemplateResponse.model_validate(t) for t in templates]
    return ApiResponse(
        success=True,
        message="Fetched templates successfully",
        data=response_data
    )


@router.post("", response_model=ApiResponse[TemplateResponse], dependencies=[Depends(require_admin)])
async def create_template(
    payload: TemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    tpl = await template_service.create_template(db, payload)
    return ApiResponse(
        success=True,
        message="Document template created successfully",
        data=TemplateResponse.model_validate(tpl)
    )


@router.put("/{id}", response_model=ApiResponse[TemplateResponse], dependencies=[Depends(require_admin)])
async def update_template(
    id: uuid.UUID,
    payload: TemplateUpdate,
    db: AsyncSession = Depends(get_db)
):
    tpl = await template_service.update_template(db, id, payload)
    return ApiResponse(
        success=True,
        message="Document template updated successfully",
        data=TemplateResponse.model_validate(tpl)
    )


@router.delete("/{id}", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def delete_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    await template_service.delete_template(db, id)
    return ApiResponse(
        success=True,
        message="Document template removed successfully",
        data={}
    )
