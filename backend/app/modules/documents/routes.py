import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, RoleRequirement
from app.modules.users.model import User
from app.modules.documents.schema import DocumentResponse
from app.modules.documents.service import document_service
from app.modules.auth.schema import ApiResponse

router = APIRouter(prefix="/documents", tags=["Documents Generation"])

require_admin = RoleRequirement(["Admin"])


@router.post("/generate", response_model=ApiResponse[DocumentResponse])
async def generate_document(
    template_id: uuid.UUID = Form(..., description="Document template UUID"),
    file: UploadFile = File(..., description="Spreadsheet data file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = await document_service.generate_document(
        db,
        user=current_user,
        template_id=template_id,
        uploaded_file=file
    )
    
    resp_data = DocumentResponse.model_validate(doc)
    # Add creator name to response
    resp_data.created_by_name = current_user.name
    if doc.template:
        resp_data.template_name = doc.template.name

    return ApiResponse(
        success=True,
        message="Document generated successfully",
        data=resp_data
    )


@router.get("/history", response_model=ApiResponse[List[DocumentResponse]])
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    docs = await document_service.list_documents(db, user=current_user)
    
    response_data = []
    for d in docs:
        item = DocumentResponse.model_validate(d)
        if d.user:
            item.created_by_name = d.user.name
        if d.template:
            item.template_name = d.template.name
        response_data.append(item)

    return ApiResponse(
        success=True,
        message="Fetched generation history successfully",
        data=response_data
    )


@router.get("/{id}", response_model=ApiResponse[DocumentResponse])
async def get_document_details(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = await document_service.get_document(db, id, current_user)
    item = DocumentResponse.model_validate(doc)
    if doc.user:
        item.created_by_name = doc.user.name
    if doc.template:
        item.template_name = doc.template.name

    return ApiResponse(
        success=True,
        message="Fetched document details successfully",
        data=item
    )


@router.delete("/{id}", response_model=ApiResponse[dict], dependencies=[Depends(require_admin)])
async def delete_document(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    await document_service.delete_document(db, id)
    return ApiResponse(
        success=True,
        message="Document record and associated files removed from platform database",
        data={}
    )
