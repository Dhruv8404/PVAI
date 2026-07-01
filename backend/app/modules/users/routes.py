import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleRequirement
from app.modules.users.model import User
from app.modules.users.schema import UserResponse, UserCreate, UserUpdate
from app.modules.users.service import user_service
from app.modules.auth.schema import ApiResponse

router = APIRouter(prefix="/users", tags=["Users Management"])

# Setup Admin guard dependency
require_admin = RoleRequirement(["Admin"])


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return ApiResponse(
        success=True,
        message="Fetched profile details successfully",
        data=UserResponse.model_validate(current_user)
    )


@router.get("", response_model=ApiResponse[List[UserResponse]], dependencies=[Depends(require_admin)])
async def get_users(
    search: str = Query(None, description="Search term for name or email"),
    role: str = Query(None, description="Filter by role name"),
    status: str = Query(None, description="Filter by status (Active/Inactive)"),
    sort_by: str = Query("name", description="Sort field name"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page index"),
    limit: int = Query(10, ge=1, le=100, description="Page size limit"),
    db: AsyncSession = Depends(get_db)
):
    users, total = await user_service.list_users(
        db,
        search=search,
        role=role,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )
    
    # We can attach count parameters in headers or simply inside response message/metadata
    response_data = [UserResponse.model_validate(u) for u in users]
    return ApiResponse(
        success=True,
        message=f"Total matches: {total}",
        data=response_data
    )


@router.get("/export", dependencies=[Depends(require_admin)])
async def export_users(
    db: AsyncSession = Depends(get_db)
):
    csv_data = await user_service.export_users_csv(db)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=users_directory.csv"
        }
    )


@router.get("/{id}", response_model=ApiResponse[UserResponse], dependencies=[Depends(require_admin)])
async def get_user_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    user = await user_service.get_user_profile(db, id)
    return ApiResponse(
        success=True,
        message="Fetched user profile details successfully",
        data=UserResponse.model_validate(user)
    )


@router.post("", response_model=ApiResponse[UserResponse], dependencies=[Depends(require_admin)])
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    user = await user_service.create_user(db, payload)
    await db.commit()
    return ApiResponse(
        success=True,
        message="Workspace account created successfully",
        data=UserResponse.model_validate(user)
    )


@router.put("/{id}", response_model=ApiResponse[UserResponse], dependencies=[Depends(require_admin)])
async def update_user(
    id: uuid.UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    user = await user_service.update_user(db, id, payload)
    await db.commit()
    return ApiResponse(
        success=True,
        message="User profile updated successfully",
        data=UserResponse.model_validate(user)
    )


@router.delete("/{id}", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def delete_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    await user_service.delete_user(db, id)
    await db.commit()
    return ApiResponse(
        success=True,
        message="User account removed successfully",
        data={}
    )


@router.post("/{id}/deactivate", response_model=ApiResponse[UserResponse], dependencies=[Depends(require_admin)])
async def deactivate_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    user = await user_service.toggle_status(db, id, "Inactive")
    await db.commit()
    return ApiResponse(
        success=True,
        message="User account deactivated successfully",
        data=UserResponse.model_validate(user)
    )


@router.post("/{id}/activate", response_model=ApiResponse[UserResponse], dependencies=[Depends(require_admin)])
async def activate_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    user = await user_service.toggle_status(db, id, "Active")
    await db.commit()
    return ApiResponse(
        success=True,
        message="User account activated successfully",
        data=UserResponse.model_validate(user)
    )


@router.post("/{id}/reset-password", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def reset_password(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    temp_pwd = await user_service.reset_password(db, id)
    await db.commit()
    return ApiResponse(
        success=True,
        message="User credentials reset successfully",
        data={"temp_password": temp_pwd}
    )
