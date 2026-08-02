import os
import uuid
import shutil
import urllib.request
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status, BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user, RoleRequirement
from app.modules.users.model import User
from app.modules.templates.model import HtmlTemplate, TemplateField, AIConfiguration
from app.modules.templates.schema import (
    HtmlTemplateResponse,
    HtmlTemplateDetailResponse,
    TemplateManifestSubmit,
    TemplateFieldResponse,
    AIConfigResponse,
    AIConfigUpdate,
    ConfirmMappingRequest,
    AnalyzeHeadersResponse,
    CustomerHeaderMappingResponse,
    ValidationLogResponse,
    StandardizedDatasetResponse,
    StandardizeDataAPIResponse
)
from app.modules.templates.services.template_service import template_service
from app.modules.auth.schema import ApiResponse

logger = logging.getLogger(__name__)



# Routers
admin_router = APIRouter(prefix="/admin/templates", tags=["Admin HTML Templates"])
public_router = APIRouter(prefix="/templates", tags=["Public HTML Templates"])
spec_router = APIRouter(prefix="/templates", tags=["Spec Templates"])

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
            from app.core.storage import StorageProviderFactory
            import tempfile
            import os
            os.makedirs("storage/temp", exist_ok=True)
            temp_fd, temp_path = tempfile.mkstemp(dir="storage/temp")
            try:
                provider = StorageProviderFactory.get_provider()
                success = provider.download_file(filepath, temp_path)
                if not success:
                    raise Exception(f"Failed to download template file from storage: {filepath}")
                with open(temp_path, "r", encoding="utf-8") as f:
                    return f.read()
            finally:
                os.close(temp_fd)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch template from storage: {str(e)}"
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
    try:
        new_tpl = await template_service.create_template_draft(
            db=db,
            file=file,
            name=name,
            version=version,
            description=description,
            uploaded_by=current_user.email
        )
        return ApiResponse(
            success=True,
            message="HTML Template uploaded successfully as Draft",
            data=HtmlTemplateResponse.model_validate(new_tpl)
        )
    except Exception as ex:
        if "already exists" in str(ex) or "Only HTML" in str(ex) or "size exceeds" in str(ex) or "structure missing" in str(ex):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@admin_router.get("", response_model=ApiResponse[List[HtmlTemplateResponse]], dependencies=[Depends(require_admin)])
async def list_html_templates(
    db: AsyncSession = Depends(get_db)
):
    tpls = await template_service.list_templates(db)
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
    try:
        tpl = await template_service.get_template(db, id)
        html_content = read_html_content(tpl.html_file)
        
        # Get related fields
        stmt_fields = select(TemplateField).where(TemplateField.template_id == id)
        res_fields = await db.execute(stmt_fields)
        fields_list = res_fields.scalars().all()
        
        response_data = HtmlTemplateDetailResponse(
            id=tpl.id,
            name=tpl.name,
            version=tpl.version,
            description=tpl.description,
            html_file=tpl.html_file,
            is_active=tpl.is_active,
            status=tpl.status,
            required_files=tpl.required_files,
            uploaded_by=tpl.uploaded_by,
            created_at=tpl.created_at,
            updated_at=tpl.updated_at,
            html_content=html_content,
            fields=[TemplateFieldResponse.model_validate(f) for f in fields_list]
        )
        return ApiResponse(
            success=True,
            message="Fetched HTML template details successfully",
            data=response_data
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@admin_router.put("/{id}/activate", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def activate_html_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        tpl = await template_service.update_template_status(db, id, True)
        return ApiResponse(
            success=True,
            message=f"HTML Template '{tpl.name}' activated successfully",
            data=HtmlTemplateResponse.model_validate(tpl)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@admin_router.put("/{id}/deactivate", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def deactivate_html_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        tpl = await template_service.update_template_status(db, id, False)
        return ApiResponse(
            success=True,
            message=f"HTML Template '{tpl.name}' deactivated successfully",
            data=HtmlTemplateResponse.model_validate(tpl)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@admin_router.delete("/{id}", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def delete_html_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        await template_service.delete_template(db, id)
        return ApiResponse(
            success=True,
            message="HTML Template deleted successfully",
            data={}
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@public_router.get("/current", response_model=ApiResponse[HtmlTemplateDetailResponse])
async def get_current_active_template(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    # Attempt to find the active template
    stmt = select(HtmlTemplate).where(HtmlTemplate.is_active == True, HtmlTemplate.is_deleted == False)
    res = await db.execute(stmt)
    tpl = res.scalar_one_or_none()

    if not tpl:
        fallback_stmt = select(HtmlTemplate).where(HtmlTemplate.is_deleted == False).order_by(HtmlTemplate.created_at.desc())
        fallback_res = await db.execute(fallback_stmt)
        tpl = fallback_res.scalars().first()

    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active or fallback HTML template available."
        )

    html_content = read_html_content(tpl.html_file)
    stmt_fields = select(TemplateField).where(TemplateField.template_id == tpl.id)
    res_fields = await db.execute(stmt_fields)
    fields_list = res_fields.scalars().all()

    response_data = HtmlTemplateDetailResponse(
        id=tpl.id,
        name=tpl.name,
        version=tpl.version,
        description=tpl.description,
        html_file=tpl.html_file,
        is_active=tpl.is_active,
        status=tpl.status,
        required_files=tpl.required_files,
        uploaded_by=tpl.uploaded_by,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
        html_content=html_content,
        fields=[TemplateFieldResponse.model_validate(f) for f in fields_list]
    )
    return ApiResponse(
        success=True,
        message="Current active template fetched successfully",
        data=response_data
    )


# Core Admin Handlers for Rename & Metadata Updates
class HtmlTemplateRename(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

class HtmlTemplateMetadataUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    version: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=255)

@admin_router.put("/{id}/rename", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def rename_html_template(
    id: uuid.UUID,
    payload: HtmlTemplateRename,
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
    tpl.name = payload.name.strip()
    await db.commit()
    await db.refresh(tpl)
    return ApiResponse(
        success=True,
        message="HTML Template renamed successfully",
        data=HtmlTemplateResponse.model_validate(tpl)
    )

@admin_router.put("/{id}/metadata", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def update_html_template_metadata(
    id: uuid.UUID,
    payload: HtmlTemplateMetadataUpdate,
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
    if payload.name is not None:
        tpl.name = payload.name.strip()
    if payload.version is not None:
        tpl.version = payload.version.strip()
    if payload.description is not None:
        tpl.description = payload.description.strip()
        
    await db.commit()
    await db.refresh(tpl)
    return ApiResponse(
        success=True,
        message="HTML Template metadata updated successfully",
        data=HtmlTemplateResponse.model_validate(tpl)
    )


# ------------------------------------------------------------
# Spec Router: Implementation of Phase 1 Template Wizard APIs
# ------------------------------------------------------------

@spec_router.post("/upload/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.post("/upload", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.post("/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.post("", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_upload_html_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Step 1: Upload template draft."""
    return await upload_html_template(file, name, version, description, db, current_user)


@spec_router.post("/{id}/manifest", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.post("/{id}/manifest/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_submit_manifest(
    id: uuid.UUID,
    payload: TemplateManifestSubmit,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Step 2: Submit manifest parameters and trigger background embedding vectorizer."""
    try:
        tpl = await template_service.submit_template_manifest(
            db=db,
            template_id=id,
            required_excel_files=payload.required_excel_files,
            required_fields=[field.model_dump() for field in payload.required_fields],
            background_tasks=background_tasks
        )
        return ApiResponse(
            success=True,
            message="Template manifest configurations registered. Embedding generation launched in background.",
            data=HtmlTemplateResponse.model_validate(tpl)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


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


@spec_router.get("/{id}/", response_model=ApiResponse[HtmlTemplateDetailResponse])
@spec_router.get("/{id}", response_model=ApiResponse[HtmlTemplateDetailResponse])
async def spec_get_template_detail(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    return await get_html_template_detail(id, db)


@spec_router.get("/{id}/fields", response_model=ApiResponse[List[TemplateFieldResponse]])
@spec_router.get("/{id}/fields/", response_model=ApiResponse[List[TemplateFieldResponse]])
async def spec_get_template_fields(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    try:
        # Check template existence
        await template_service.get_template(db, id)
        
        stmt = select(TemplateField).where(TemplateField.template_id == id)
        res = await db.execute(stmt)
        fields = res.scalars().all()
        
        return ApiResponse(
            success=True,
            message="Extracted template fields retrieved successfully",
            data=[TemplateFieldResponse.model_validate(f) for f in fields]
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


class StatusUpdatePayload(BaseModel):
    is_active: bool


@spec_router.patch("/{id}/status", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.patch("/{id}/status/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_patch_template_status(
    id: uuid.UUID,
    payload: StatusUpdatePayload,
    db: AsyncSession = Depends(get_db)
):
    try:
        tpl = await template_service.update_template_status(db, id, payload.is_active)
        return ApiResponse(
            success=True,
            message=f"Template activation status set to: {payload.is_active}",
            data=HtmlTemplateResponse.model_validate(tpl)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@spec_router.delete("/{id}/", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
@spec_router.delete("/{id}", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def spec_delete_template(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await delete_html_template(id, db)


@spec_router.put("/{id}/rename/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.put("/{id}/rename", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_rename_template(
    id: uuid.UUID,
    payload: HtmlTemplateRename,
    db: AsyncSession = Depends(get_db)
):
    return await rename_html_template(id, payload, db)


@spec_router.put("/{id}/metadata/", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
@spec_router.put("/{id}/metadata", response_model=ApiResponse[HtmlTemplateResponse], dependencies=[Depends(require_admin)])
async def spec_update_template_metadata(
    id: uuid.UUID,
    payload: HtmlTemplateMetadataUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await update_html_template_metadata(id, payload, db)


@spec_router.get("/ai-config", response_model=ApiResponse[AIConfigResponse])
@spec_router.get("/ai-config/", response_model=ApiResponse[AIConfigResponse])
async def spec_get_ai_config(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    config = await template_service.get_ai_config(db)
    return ApiResponse(
        success=True,
        message="Fetched AI configuration successfully",
        data=AIConfigResponse.model_validate(config)
    )


@spec_router.put("/ai-config", response_model=ApiResponse[AIConfigResponse], dependencies=[Depends(require_admin)])
@spec_router.put("/ai-config/", response_model=ApiResponse[AIConfigResponse], dependencies=[Depends(require_admin)])
async def spec_update_ai_config(
    payload: AIConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        config = await template_service.update_ai_config(db, payload.model_dump(exclude_unset=True))
        return ApiResponse(
            success=True,
            message="AI configuration settings updated successfully",
            data=AIConfigResponse.model_validate(config)
        )
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@spec_router.post("/{id}/analyze-headers", response_model=ApiResponse[AnalyzeHeadersResponse])
@spec_router.post("/{id}/analyze-headers/", response_model=ApiResponse[AnalyzeHeadersResponse])
async def spec_analyze_headers(
    id: uuid.UUID,
    files: List[UploadFile] = File(...),
    customer_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Multipart form endpoint to parse Excel headers and map them to template target fields."""
    try:
        from app.modules.templates.services.header_mapping_coordinator import header_mapping_coordinator
        res = await header_mapping_coordinator.analyze_uploaded_headers(
            db=db,
            template_id=id,
            customer_id=customer_id,
            files=files
        )
        return ApiResponse(
            success=True,
            message="Excel header mapping analysis completed",
            data=AnalyzeHeadersResponse.model_validate(res)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@spec_router.post("/{id}/confirm-mapping", response_model=ApiResponse[dict])
@spec_router.post("/{id}/confirm-mapping/", response_model=ApiResponse[dict])
async def spec_confirm_mapping(
    id: uuid.UUID,
    payload: ConfirmMappingRequest,
    db: AsyncSession = Depends(get_db)
):
    """Saves admin-confirmed custom mappings into the database cache."""
    try:
        from app.modules.templates.services.header_mapping_coordinator import header_mapping_coordinator
        await header_mapping_coordinator.confirm_manual_mappings(
            db=db,
            template_id=id,
            customer_id=payload.customer_id,
            mappings=[item.model_dump() for item in payload.mappings]
        )
        return ApiResponse(
            success=True,
            message="Manual mappings confirmed and cached successfully",
            data={}
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@spec_router.get("/{id}/mapping-history", response_model=ApiResponse[List[CustomerHeaderMappingResponse]])
@spec_router.get("/{id}/mapping-history/", response_model=ApiResponse[List[CustomerHeaderMappingResponse]])
async def spec_get_mapping_history(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Retrieves previous customer mappings logs mapped to this template."""
    try:
        from app.modules.templates.services.mapping_cache_service import mapping_cache_service
        history = await mapping_cache_service.get_mapping_history(db, id)
        return ApiResponse(
            success=True,
            message="Fetched mapping history successfully",
            data=[CustomerHeaderMappingResponse.model_validate(h) for h in history]
        )
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@spec_router.post("/{id}/standardize-data", response_model=ApiResponse[StandardizeDataAPIResponse])
@spec_router.post("/{id}/standardize-data/", response_model=ApiResponse[StandardizeDataAPIResponse])
async def spec_standardize_data(
    id: uuid.UUID,
    files: List[UploadFile] = File(...),
    customer_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Parses, normalizes, merges, and validates customer Excel spreadsheets under one template."""
    try:
        from app.modules.templates.services.data_standardization_coordinator import data_standardization_coordinator
        dataset = await data_standardization_coordinator.standardize_customer_data(
            db=db,
            template_id=id,
            customer_id=customer_id,
            files=files
        )
        
        # Calculate summary counts for API response
        errs = dataset.statistics.get("errors", 0)
        warns = dataset.statistics.get("warnings", 0)
        
        response_payload = {
            "dataset_id": dataset.id,
            "statistics": dataset.statistics,
            "validation_summary": {
                "errors": errs,
                "warnings": warns
            },
            "data": dataset.data
        }
        
        return ApiResponse(
            success=True,
            message="Data extraction and standardization pipeline completed",
            data=response_payload
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except ValidationException as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@spec_router.get("/{id}/validation", response_model=ApiResponse[List[ValidationLogResponse]])
@spec_router.get("/{id}/validation/", response_model=ApiResponse[List[ValidationLogResponse]])
async def spec_get_validation_logs(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Retrieves validation logs for the last processed dataset matching this template."""
    try:
        from app.modules.templates.services.data_standardization_coordinator import data_standardization_coordinator
        logs = await data_standardization_coordinator.get_validation_logs(db, id)
        return ApiResponse(
            success=True,
            message="Fetched validation logs successfully",
            data=[ValidationLogResponse.model_validate(l) for l in logs]
        )
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@spec_router.get("/{id}/dataset/{dataset_id}", response_model=ApiResponse[StandardizedDatasetResponse])
@spec_router.get("/{id}/dataset/{dataset_id}/", response_model=ApiResponse[StandardizedDatasetResponse])
async def spec_get_standardized_dataset(
    id: uuid.UUID,
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Retrieves standard grouped JSON records and processing statistics by dataset UUID."""
    try:
        from app.modules.templates.services.data_standardization_coordinator import data_standardization_coordinator
        dataset = await data_standardization_coordinator.get_dataset(db, dataset_id)
        return ApiResponse(
            success=True,
            message="Fetched standardized dataset successfully",
            data=StandardizedDatasetResponse.model_validate(dataset)
        )
    except NotFoundException as nfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


