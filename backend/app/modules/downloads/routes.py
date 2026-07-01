import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleRequirement
from app.modules.users.model import User
from app.modules.downloads.schema import DownloadLogResponse
from app.modules.downloads.service import download_service
from app.modules.auth.schema import ApiResponse

router = APIRouter(prefix="/downloads", tags=["Downloads Management"])

require_admin = RoleRequirement(["Admin"])


@router.get("/{doc_id}")
async def download_file(
    doc_id: uuid.UUID,
    format: str = Query("HTML", description="Target download format (HTML/PDF)"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    client_ip = request.client.host if request and request.client else "unknown"
    
    file_bytes, filename = await download_service.get_document_for_download(
        db,
        doc_id=doc_id,
        user=current_user,
        client_ip=client_ip,
        file_format=format
    )

    media_type = "text/html" if format.upper() == "HTML" else "application/pdf"
    
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/logs", response_model=ApiResponse[List[DownloadLogResponse]], dependencies=[Depends(require_admin)])
async def get_download_logs(
    limit: int = Query(100, le=1000, description="Audit logs limit"),
    db: AsyncSession = Depends(get_db)
):
    logs = await download_service.list_logs(db, limit=limit)
    
    response_data = []
    for log in logs:
        item = DownloadLogResponse.model_validate(log)
        if log.document:
            item.document_name = log.document.name
        if log.user:
            item.user_name = log.user.name
            item.user_email = log.user.email
        response_data.append(item)

    return ApiResponse(
        success=True,
        message="Fetched download audit logs successfully",
        data=response_data
    )
