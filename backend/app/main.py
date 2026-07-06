from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
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
from app.modules.templates.html_routes import admin_router as html_admin_router, public_router as html_public_router, spec_router as html_spec_router
from app.modules.documents.routes import router as documents_router
from app.modules.downloads.routes import router as downloads_router
from app.modules.dashboard.routes import router as dashboard_router

# Import models for seeding
from app.modules.users.model import User, Role, Permission
from app.modules.templates.model import DocumentTemplate, HtmlTemplate


# Lifespan manager to seed default models
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create tables in development (In production, use Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Ensure new generated_documents columns exist for PostgreSQL/Neon DB migrations
        for col_name, col_type in [
            ("template_version", "VARCHAR(50) DEFAULT '1.0.0'"),
            ("report_type", "VARCHAR(50) DEFAULT 'PSUR'"),
            ("generated_file_size", "INTEGER DEFAULT 0"),
            ("download_count", "INTEGER DEFAULT 0"),
            ("last_downloaded_at", "TIMESTAMP WITH TIME ZONE"),
            ("browser", "VARCHAR(255)"),
            ("ip_address", "VARCHAR(50)"),
            ("failed_reason", "VARCHAR(500)"),
        ]:
            try:
                await conn.execute(
                    text(f"ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                )
            except Exception:
                # Fallback / ignore error if column already exists or SQLite dialect compatibility
                pass

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

        # Seed default HTML template if table is empty
        stmt_html = select(HtmlTemplate)
        res_html = await db.execute(stmt_html)
        html_tpls = res_html.scalars().all()
        if not html_tpls:
            import os
            import shutil
            os.makedirs(settings.TEMPLATES_DIR, exist_ok=True)
            app_dir = os.path.dirname(os.path.abspath(__file__))
            default_src = os.path.join(app_dir, "templates", "drafting_studio.html")
            default_dest = os.path.join(settings.TEMPLATES_DIR, "default_drafting_studio.html")
            if os.path.exists(default_src):
                shutil.copy2(default_src, default_dest)
                default_tpl = HtmlTemplate(
                    name="Default Drafting Studio",
                    version="1.0.0",
                    description="Standard bundled PV drafting studio template",
                    html_file=default_dest,
                    is_active=True,
                    is_deleted=False,
                    uploaded_by="system@company.com"
                )
                db.add(default_tpl)
                await db.commit()
                print("[SEEDER] Default HTML template seeded successfully")
            else:
                print(f"[SEEDER] ERROR: Default HTML template source not found at {default_src}")
            
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
app.include_router(html_admin_router, prefix=settings.API_V1_STR)
app.include_router(html_public_router, prefix=settings.API_V1_STR)
app.include_router(html_spec_router, prefix="/api")
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(downloads_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
