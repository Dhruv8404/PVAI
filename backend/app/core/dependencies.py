from typing import AsyncGenerator
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.core.exceptions import AuthException, ForbiddenException
from app.modules.users.model import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


# Dependency to resolve current user session
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if not user_email or token_type != "access":
            raise AuthException("Invalid access token credentials")
    except JWTError:
        raise AuthException("Access token session expired or signature corrupted")

    # Fetch user from db
    stmt = select(User).where(User.email == user_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthException("User record not found in system directory")
    if user.status != "Active":
        raise AuthException("Workspace seat deactivated. Please contact support")
        
    return user


# Permission enforcement guard dependency factory
class PermissionRequirement:
    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        # Admins bypass permission constraints
        user_roles_list = [r.name for r in current_user.roles]
        if "Admin" in user_roles_list:
            return current_user
            
        # Compile user permissions list
        user_perms = set()
        for role in current_user.roles:
            for perm in role.permissions:
                user_perms.add(perm.name)
                
        # Verify required permissions
        for perm in self.required_permissions:
            if perm not in user_perms:
                raise ForbiddenException(
                    f"Required permission scope '{perm}' was missing for user roles"
                )
                
        return current_user


# Quick wrapper for role check
class RoleRequirement:
    def __init__(self, required_roles: list[str]):
        self.required_roles = required_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_roles_list = [r.name for r in current_user.roles]
        
        # Check if user holds any of the required roles
        has_role = any(role in user_roles_list for role in self.required_roles)
        if not has_role:
            raise ForbiddenException("Administrative access privileges required")
            
        return current_user
