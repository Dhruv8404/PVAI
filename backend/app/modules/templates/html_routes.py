import os
import uuid
import shutil
import urllib.request
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import cloudinary
import cloudinary.uploader

from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user, RoleRequirement
from app.modules.users.model import User
from app.modules.templates.model import HtmlTemplate
from app.modules.templates.schema import HtmlTemplateResponse, HtmlTemplateDetailResponse
from app.modules.auth.schema import ApiResponse

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

# Routers
admin_router = APIRouter(prefix="/admin/templates", tags=["Admin HTML Templates"])
public_router = APIRouter(prefix="/templates", tags=["Public HTML Templates"])

# Guards
require_admin = RoleRequirement(["Admin"])

# Helper to read HTML content safely (supports local files and Cloudinary URL targets)
def read_html_content(filepath: str) -> str:
    if not filepath:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template file path/URL is empty."
        )
    
    if filepath.startswith("http://") or filepath.startswith("https://"):
        try:
            req = urllib.request.Request(
                filepath, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch template from Cloudinary URL: {str(e)}"
            )
    else:
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template HTML file not found on disk"
            )
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read template content: {str(e)}"
            )


@admin_router.post("/upload", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def upload_html_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validate file extension
    if not file.filename or not file.filename.lower().endswith(".html"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTML files (.html) are allowed."
        )

    # 2. Validate file size (limit to 5MB)
    max_size = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HTML template file size exceeds the 5MB limit."
        )
    await file.seek(0) # Reset stream pointer

    # 3. Save file uniquely (either Cloudinary or Local)
    if settings.STORAGE_TYPE == "cloudinary":
        try:
            upload_result = cloudinary.uploader.upload(
                content,
                resource_type="raw",
                folder="pv_templates",
                public_id=f"{uuid.uuid4().hex}.html"
            )
            filepath = upload_result.get("secure_url")
            if not filepath:
                raise Exception("Cloudinary secure_url is empty in response.")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload template to Cloudinary: {str(e)}"
            )
    else:
        # Ensure template directory exists
        os.makedirs(settings.TEMPLATES_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.html"
        filepath = os.path.join(settings.TEMPLATES_DIR, filename)
        try:
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write template file to storage: {str(e)}"
            )

    # 4. Save metadata to database
    new_tpl = HtmlTemplate(
        name=name.strip(),
        version=version.strip(),
        description=description.strip() if description else None,
        html_file=filepath,
        is_active=False,
        is_deleted=False,
        uploaded_by=current_user.email
    )
    db.add(new_tpl)
    await db.commit()
    await db.refresh(new_tpl)

    return ApiResponse(
        success=True,
        message="HTML Template uploaded successfully",
        data=HtmlTemplateResponse.model_validate(new_tpl)
    )


@admin_router.get("", response_model=ApiResponse[List[HtmlTemplateResponse]], dependencies=[Depends(require_admin)])
async def list_html_templates(
    db: AsyncSession = Depends(get_db)
):
    stmt = select(HtmlTemplate).where(HtmlTemplate.is_deleted == False).order_by(HtmlTemplate.created_at.desc())
    res = await db.execute(stmt)
    tpls = res.scalars().all()
    return ApiResponse(
        success=True,
        message="Fetched HTML templates successfully",
        data=[HtmlTemplateResponse.model_validate(t) for t in tpls]
    )


@admin_router.get("/{id}", response_model=ApiResponse[HtmlTemplateDetailResponse], dependencies=[Depends(require_admin)])
async def get_html_template_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(HtmlTemplate).where(HtmlTemplate.id == id, HtmlTemplate.is_deleted == False)
    res = await db.execute(stmt)
    tpl = res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTML template not found."
        )

    html_content = read_html_content(tpl.html_file)
    response_data = HtmlTemplateDetailResponse(
        id=tpl.id,
        name=tpl.name,
        version=tpl.version,
        description=tpl.description,
        html_file=tpl.html_file,
        is_active=tpl.is_active,
        uploaded_by=tpl.uploaded_by,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
        html_content=html_content
    )
    return ApiResponse(
        success=True,
        message="Fetched HTML template details successfully",
        data=response_data
    )


@admin_router.put("/{id}/activate", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def activate_html_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(HtmlTemplate).where(HtmlTemplate.id == id, HtmlTemplate.is_deleted == False)
    res = await db.execute(stmt)
    tpl = res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTML template not found."
        )

    # Deactivate all other templates
    await db.execute(
        update(HtmlTemplate)
        .where(HtmlTemplate.id != id)
        .values(is_active=False)
    )

    tpl.is_active = True
    await db.commit()
    await db.refresh(tpl)

    return ApiResponse(
        success=True,
        message=f"HTML Template '{tpl.name}' activated successfully",
        data=HtmlTemplateResponse.model_validate(tpl)
    )


@admin_router.put("/{id}/deactivate", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def deactivate_html_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(HtmlTemplate).where(HtmlTemplate.id == id, HtmlTemplate.is_deleted == False)
    res = await db.execute(stmt)
    tpl = res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTML template not found."
        )

    tpl.is_active = False
    await db.commit()
    await db.refresh(tpl)

    return ApiResponse(
        success=True,
        message=f"HTML Template '{tpl.name}' deactivated successfully",
        data=HtmlTemplateResponse.model_validate(tpl)
    )


@admin_router.delete("/{id}", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def delete_html_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(HtmlTemplate).where(HtmlTemplate.id == id, HtmlTemplate.is_deleted == False)
    res = await db.execute(stmt)
    tpl = res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTML template not found."
        )

    # Reject deletion of active template
    if tpl.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active template. Please activate another template first."
        )

    # Soft delete
    tpl.is_deleted = True
    await db.commit()

    return ApiResponse(
        success=True,
        message="HTML Template deleted successfully",
        data={}
    )


@public_router.get("/current", response_model=ApiResponse[HtmlTemplateDetailResponse])
async def get_current_active_template(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user) # Secure: only authenticated users can consume
):
    # 1. Attempt to find the active template
    stmt = select(HtmlTemplate).where(HtmlTemplate.is_active == True, HtmlTemplate.is_deleted == False)
    res = await db.execute(stmt)
    tpl = res.scalar_one_or_none()

    # 2. If no active template, fall back to the latest non-deleted template
    if not tpl:
        fallback_stmt = select(HtmlTemplate).where(HtmlTemplate.is_deleted == False).order_by(HtmlTemplate.created_at.desc())
        fallback_res = await db.execute(fallback_stmt)
        tpl = fallback_res.scalars().first()

    # 3. If still nothing, raise error
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active or fallback HTML template available."
        )

    html_content = read_html_content(tpl.html_file)
    response_data = HtmlTemplateDetailResponse(
        id=tpl.id,
        name=tpl.name,
        version=tpl.version,
        description=tpl.description,
        html_file=tpl.html_file,
        is_active=tpl.is_active,
        uploaded_by=tpl.uploaded_by,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
        html_content=html_content
    )
    return ApiResponse(
        success=True,
        message="Current active template fetched successfully",
        data=response_data
    )


# Spec Router to match exact /api/templates/ paths requested in requirements
spec_router = APIRouter(prefix="/templates", tags=["Spec Templates"])

@spec_router.post("/upload/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.post("/upload", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_upload_html_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await upload_html_template(file, name, version, description, db, current_user)


@spec_router.get("/", response_model=ApiResponse[List[HtmlTemplateResponse]])
@spec_router.get("", response_model=ApiResponse[List[HtmlTemplateResponse]])
async def spec_list_html_templates(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    return await list_html_templates(db)


@spec_router.get("/active/", response_model=ApiResponse[HtmlTemplateDetailResponse])
@spec_router.get("/active", response_model=ApiResponse[HtmlTemplateDetailResponse])
async def spec_get_active_template(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    return await get_current_active_template(db, _current_user)


@spec_router.put("/{id}/activate/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.put("/{id}/activate", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_activate_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await activate_html_template(id, db)


@spec_router.put("/{id}/deactivate/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.put("/{id}/deactivate", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_deactivate_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await deactivate_html_template(id, db)


@spec_router.get("/{id}/", response_model=ApiResponse[HtmlTemplateDetailResponse], dependencies=[Depends(require_admin)])
@spec_router.get("/{id}", response_model=ApiResponse[HtmlTemplateDetailResponse], dependencies=[Depends(require_admin)])
async def spec_get_template_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await get_html_template_detail(id, db)


@spec_router.delete("/{id}/", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
@spec_router.delete("/{id}", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def spec_delete_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await delete_html_template(id, db)

