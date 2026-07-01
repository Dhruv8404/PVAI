import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.repository import BaseRepository
from app.core.security import get_password_hash
from app.modules.users.model import User, Role
from app.modules.templates.model import DocumentTemplate
from app.modules.users.schema import UserCreate, UserUpdate


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        # Allocate Role (look up role by name)
        role_stmt = select(Role).where(Role.name == obj_in.role)
        role_res = await db.execute(role_stmt)
        role = role_res.scalar_one_or_none()
        
        if not role:
            # Seed default Role if not exists
            role = Role(name=obj_in.role, description=f"Default role for {obj_in.role}")
            db.add(role)
            await db.flush()

        # Allocate allowed document templates
        templates = []
        if obj_in.allowed_templates:
            for tpl_id in obj_in.allowed_templates:
                tpl_stmt = select(DocumentTemplate).where(DocumentTemplate.id == tpl_id)
                tpl_res = await db.execute(tpl_stmt)
                tpl = tpl_res.scalar_one_or_none()
                if tpl:
                    templates.append(tpl)

        # Create user record with relationships pre-populated to avoid lazy load mutations
        hashed_password = get_password_hash(obj_in.password)
        db_obj = User(
            name=obj_in.name,
            email=obj_in.email,
            hashed_password=hashed_password,
            status=obj_in.status,
            report_limit=obj_in.report_limit,
            roles=[role],
            allowed_templates=templates
        )
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def update_user(self, db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Handle password separately if provided (though standard is update profile only)
        if "password" in update_data and update_data["password"]:
            db_obj.hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]

        # Handle simple fields
        for field in ["name", "email", "status", "report_limit"]:
            if field in update_data and update_data[field] is not None:
                setattr(db_obj, field, update_data[field])

        # Handle roles if provided
        if "role" in update_data and update_data["role"]:
            role_name = update_data["role"]
            role_stmt = select(Role).where(Role.name == role_name)
            role_res = await db.execute(role_stmt)
            role = role_res.scalar_one_or_none()
            if role:
                db_obj.roles = [role]

        # Handle template permissions
        if "allowed_templates" in update_data and update_data["allowed_templates"] is not None:
            db_obj.allowed_templates.clear()
            for tpl_id in update_data["allowed_templates"]:
                tpl_stmt = select(DocumentTemplate).where(DocumentTemplate.id == tpl_id)
                tpl_res = await db.execute(tpl_stmt)
                tpl = tpl_res.scalar_one_or_none()
                if tpl:
                    db_obj.allowed_templates.append(tpl)

        db.add(db_obj)
        await db.flush()
        return db_obj


user_repository = UserRepository()
