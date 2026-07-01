from fastapi import APIRouter, Depends, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import get_password_hash
from app.modules.users.model import User
from app.modules.auth.schema import (
    ApiResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest
)
from app.modules.auth.service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=ApiResponse[dict])
async def register(
    register_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    user = await auth_service.register_user(db, register_data)
    await db.commit()
    return ApiResponse(
        success=True,
        message="Account registered successfully. Verify login credentials",
        data={"id": str(user.id), "email": user.email, "name": user.name}
    )


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    tokens = await auth_service.authenticate(db, login_data.email, login_data.password)
    return ApiResponse(
        success=True,
        message="Session authenticated successfully",
        data=tokens
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_token(
    refresh_token: str = Header(..., description="Refresh Token string")
):
    tokens = await auth_service.refresh_access_token(refresh_token)
    return ApiResponse(
        success=True,
        message="Access token refreshed successfully",
        data=tokens
    )


@router.post("/forgot-password", response_model=ApiResponse[dict])
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    token = await auth_service.generate_recovery_token(db, payload.email)
    
    # Simulate email trigger
    if token:
        background_tasks.add_task(
            print, f"[EMAIL-SIMULATION] Recovery token to reset password for {payload.email}: {token}"
        )
        
    await db.commit()
    return ApiResponse(
        success=True,
        message="If registered, recovery token sequence has been dispatched",
        data={}
    )


@router.post("/reset-password", response_model=ApiResponse[dict])
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    await auth_service.reset_password_with_token(db, payload.token, payload.password)
    await db.commit()
    return ApiResponse(
        success=True,
        message="Credentials updated successfully",
        data={}
    )


@router.post("/change-password", response_model=ApiResponse[dict])
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.core.exceptions import AuthException
    from app.core.security import verify_password
    
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise AuthException("Incorrect old password credential")
        
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.add(current_user)
    await db.flush()
    await db.commit()
    
    return ApiResponse(
        success=True,
        message="Password updated successfully",
        data={}
    )
