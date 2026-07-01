from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_middlewares
from app.core.security import get_password_hash

# Import routers
from app.modules.auth.routes import router as auth_router
from app.modules.users.routes import router as users_router
from app.modules.templates.routes import router as templates_router
from app.modules.documents.routes import router as documents_router
from app.modules.downloads.routes import router as downloads_router
from app.modules.dashboard.routes import router as dashboard_router

# Import models for seeding
from app.modules.users.model import User, Role, Permission
from app.modules.templates.model import DocumentTemplate


# Lifespan manager to seed default models
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create tables in development (In production, use Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Seed default roles and admin accounts
    async with SessionLocal() as db:
        # Check if roles exist
        stmt = select(Role)
        res = await db.execute(stmt)
        roles = res.scalars().all()
        
        if not roles:
            admin_role = Role(name="Admin", description="Administrator permissions")
            user_role = Role(name="User", description="Standard user permissions")
            db.add_all([admin_role, user_role])
            await db.flush()

            # Seed default templates
            psur_tpl = DocumentTemplate(
                name="PSUR Event Summary",
                description="Periodic safety update report event summaries compiler",
                version="1.0.0",
                required_files=["Event ID", "Severity", "Date"],
                status="Active"
            )
            quant_tpl = DocumentTemplate(
                name="Quantitative Method",
                description="Z-Score safety methods indicators compiler",
                version="2.1.0",
                required_files=["Method ID", "Value", "Z-Score"],
                status="Active"
            )
            pv_tpl = DocumentTemplate(
                name="PV Auto Tool",
                description="Automated signal detections PRR compiler",
                version="1.0.0",
                required_files=["ID", "AutoCode", "Priority"],
                status="Active"
            )
            db.add_all([psur_tpl, quant_tpl, pv_tpl])
            await db.flush()

            # Seed default users
            admin_pwd = get_password_hash("Password123!")
            admin_user = User(
                name="Sarah Connor",
                email="admin@company.com",
                hashed_password=admin_pwd,
                status="Active"
            )
            admin_user.roles.append(admin_role)
            # Give admin access to all templates
            admin_user.allowed_templates.extend([psur_tpl, quant_tpl, pv_tpl])

            user_pwd = get_password_hash("Password123!")
            standard_user = User(
                name="Alex Mercer",
                email="user@company.com",
                hashed_password=user_pwd,
                status="Active"
            )
            standard_user.roles.append(user_role)
            # Give standard user access to PSUR and PV Auto Tool
            standard_user.allowed_templates.extend([psur_tpl, pv_tpl])

            db.add_all([admin_user, standard_user])
            await db.commit()
            print("[SEEDER] Default Admin and User accounts created successfully")
            
    yield
    # Shutdown logic
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Setup core modules
setup_middlewares(app)
setup_exception_handlers(app)

# Register routes under v1 Prefix
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(templates_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(downloads_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
