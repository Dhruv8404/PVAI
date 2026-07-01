from datetime import timedelta, UTC, datetime
from typing import Optional
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    ALGORITHM
)
from app.core.exceptions import AuthException, ValidationException
from app.modules.users.repository import user_repository
from app.modules.users.model import User
from app.modules.users.schema import UserCreate
from app.modules.auth.schema import TokenResponse, UserRegister


class AuthService:
    async def authenticate(
        self, db: AsyncSession, email: str, password: str
    ) -> TokenResponse:
        user = await user_repository.get_by_email(db, email)
        if not user:
            raise AuthException("Incorrect email or password combination")
            
        if not verify_password(password, user.hashed_password):
            raise AuthException("Incorrect email or password combination")
            
        if user.status != "Active":
            raise AuthException("Your account is deactivated. Contact administrator")

        # Generate tokens
        access = create_access_token(subject=user.email)
        refresh = create_refresh_token(subject=user.email)
        
        return TokenResponse(access_token=access, refresh_token=refresh)

    async def register_user(self, db: AsyncSession, register_data: UserRegister) -> User:
        # Check if email is already in use
        existing = await user_repository.get_by_email(db, register_data.email)
        if existing:
            raise ValidationException("Email address already registered")

        user_in = UserCreate(
            email=register_data.email,
            name=register_data.name,
            password=register_data.password,
            role="User",
            status="Active",
            allowed_templates=[] # Empty by default, admin allocates
        )
        
        return await user_repository.create_user(db, obj_in=user_in)

    async def refresh_access_token(self, token: str) -> TokenResponse:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_email: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if not user_email or token_type != "refresh":
                raise AuthException("Invalid refresh token credentials")
        except JWTError:
            raise AuthException("Refresh token session expired or signature corrupted")

        # Create new tokens
        access = create_access_token(subject=user_email)
        refresh = create_refresh_token(subject=user_email)
        return TokenResponse(access_token=access, refresh_token=refresh)

    async def generate_recovery_token(self, db: AsyncSession, email: str) -> str:
        user = await user_repository.get_by_email(db, email)
        if not user:
            # Silence error for safety to prevent user enumeration
            return ""
            
        # Create token expiring in 15 minutes
        expire = datetime.now(UTC) + timedelta(minutes=15)
        to_encode = {"exp": expire, "sub": user.email, "type": "recovery"}
        encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded

    async def reset_password_with_token(
        self, db: AsyncSession, token: str, new_password: str
    ) -> bool:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_email: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if not user_email or token_type != "recovery":
                raise AuthException("Invalid recovery token payload")
        except JWTError:
            raise AuthException("Recovery token session expired or signature corrupted")

        user = await user_repository.get_by_email(db, user_email)
        if not user:
            raise AuthException("User record not found in system directory")

        # Update password hash
        from app.core.security import get_password_hash
        user.hashed_password = get_password_hash(new_password)
        db.add(user)
        await db.flush()
        return True


auth_service = AuthService()
