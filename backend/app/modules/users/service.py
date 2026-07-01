import uuid
import csv
import io
from typing import List, Optional, Tuple
from sqlalchemy import select, or_, and_, asc, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ValidationException
from app.modules.users.model import User, Role
from app.modules.users.repository import user_repository
from app.modules.users.schema import UserCreate, UserUpdate


class UserService:
    async def list_users(
        self,
        db: AsyncSession,
        *,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[User], int]:
        # Build query
        stmt = select(User)
        
        # Search criteria
        filters = []
        if search:
            filters.append(
                or_(
                    User.name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )
            
        if status:
            filters.append(User.status == status)

        if role:
            stmt = stmt.join(User.roles).where(Role.name == role)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count total matches before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        # Apply sorting
        order_col = getattr(User, sort_by, User.name)
        if sort_order == "desc":
            stmt = stmt.order_by(desc(order_col))
        else:
            stmt = stmt.order_by(asc(order_col))

        # Apply pagination
        skip = (page - 1) * limit
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        users = list(result.scalars().all())
        return users, total

    async def get_user_profile(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repository.get(db, user_id)
        if not user:
            raise NotFoundException("User profile not found")
        return user

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        # Check email uniqueness
        existing = await user_repository.get_by_email(db, user_in.email)
        if existing:
            raise ValidationException("Email address already registered")
            
        return await user_repository.create_user(db, obj_in=user_in)

    async def update_user(
        self, db: AsyncSession, user_id: uuid.UUID, user_in: UserUpdate
    ) -> User:
        user = await user_repository.get(db, user_id)
        if not user:
            raise NotFoundException("User record not found")
            
        return await user_repository.update_user(db, db_obj=user, obj_in=user_in)

    async def delete_user(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repository.get(db, user_id)
        if not user:
            raise NotFoundException("User record not found")
            
        return await user_repository.remove(db, id=user_id)

    async def toggle_status(self, db: AsyncSession, user_id: uuid.UUID, status: str) -> User:
        user = await user_repository.get(db, user_id)
        if not user:
            raise NotFoundException("User record not found")
            
        user.status = status
        db.add(user)
        await db.flush()
        return user

    async def reset_password(self, db: AsyncSession, user_id: uuid.UUID) -> str:
        user = await user_repository.get(db, user_id)
        if not user:
            raise NotFoundException("User record not found")
            
        # Generate temporary credentials string
        import random
        import string
        temp_pwd = "".join(random.choices(string.ascii_letters + string.digits, k=10)) + "!"
        
        from app.core.security import get_password_hash
        user.hashed_password = get_password_hash(temp_pwd)
        db.add(user)
        await db.flush()
        return temp_pwd

    async def export_users_csv(self, db: AsyncSession) -> str:
        users = await user_repository.get_multi(db, limit=1000)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow(["ID", "Name", "Email", "Role", "Status", "Created At"])
        for u in users:
            role_names = ", ".join([r.name for r in u.roles])
            writer.writerow([
                str(u.id),
                u.name,
                u.email,
                role_names,
                u.status,
                u.created_at.isoformat()
            ])
            
        return output.getvalue()


user_service = UserService()
