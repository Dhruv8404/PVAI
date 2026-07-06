import uuid
import time
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ValidationException, NotFoundException, ForbiddenException
from app.core.storage import get_storage
from app.modules.documents.model import GeneratedDocument
from app.modules.documents.repository import document_repository
from app.modules.documents.generator import get_generator_strategy
from app.modules.templates.repository import template_repository
from app.modules.users.model import User


class DocumentService:
    async def generate_document(
        self,
        db: AsyncSession,
        *,
        user: User,
        template_id: uuid.UUID,
        uploaded_file: UploadFile
    ) -> GeneratedDocument:
        # Check template access permissions
        user_templates_ids = [t.id for t in user.allowed_templates]
        user_roles = [r.name for r in user.roles]
        
        # Admin can access all templates, User must be authorized
        if "Admin" not in user_roles and template_id not in user_templates_ids:
            raise ForbiddenException("You do not have access rights to launch this generator template")

        # Enforce Report Generation Limits for standard Users
        if "Admin" not in user_roles:
            count_stmt = select(func.count(GeneratedDocument.id)).where(
                and_(
                    GeneratedDocument.user_id == user.id,
                    GeneratedDocument.status == "Success"
                )
            )
            count_res = await db.execute(count_stmt)
            generated_count = count_res.scalar() or 0
            if generated_count >= user.report_limit:
                raise ForbiddenException(
                    f"You have reached your report generation quota limit of {user.report_limit} reports. "
                    "Please contact an administrator to increase your allocation limit."
                )

        # Fetch template metadata
        tpl = await template_repository.get(db, template_id)
        if not tpl or tpl.status != "Active":
            raise NotFoundException("Active document template not found")

        # Resolve strategy matching template name key
        # For simplicity, we match by name key mapping
        name_key = "psur" if "psur" in tpl.name.lower() else "quant" if "quant" in tpl.name.lower() else "pv_auto"
        strategy = get_generator_strategy(name_key)

        # Read file content
        content = await uploaded_file.read()
        
        # 1. Validate spreadsheet headers structure
        strategy.validate_files(uploaded_file.filename, content)

        # Start execution timer
        start_time = time.time()

        # 2. Store upload spreadsheet file
        storage = get_storage()
        upload_subpath = f"uploads/{uuid.uuid4()}_{uploaded_file.filename}"
        saved_upload_path = await storage.save_file(content, upload_subpath)

        # 3. Process report rows compilation
        results_data = strategy.process(content)

        # 4. Generate HTML layout content
        html_markup = strategy.generate_html(results_data, uploaded_file.filename)

        # 5. Save generated HTML markup file
        html_subpath = f"generated/html/{uuid.uuid4()}_{uploaded_file.filename.split('.')[0]}.html"
        saved_html_path = await storage.save_file(html_markup.encode('utf-8'), html_subpath)

        # Stop timer
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 6. Save history log entry to DB
        doc_in_data = {
            "user_id": user.id,
            "template_id": tpl.id,
            "name": f"{tpl.name.upper()}_Report_{new_date_label()}",
            "excel_file_name": uploaded_file.filename,
            "html_path": saved_html_path,
            "pdf_path": None, # Future expansion
            "status": "Success",
            "execution_time_ms": elapsed_ms
        }
        
        doc = await document_repository.create(db, obj_in_data=doc_in_data)
        
        # Log audit details
        from app.modules.users.model import User
        # Write audit logs directly if needed or delegate to service. Here we just commit.
        return doc

    async def list_documents(
        self, db: AsyncSession, *, user: User
    ) -> List[GeneratedDocument]:
        user_roles = [r.name for r in user.roles]
        if "Admin" in user_roles:
            return await document_repository.get_all_with_relations(db)
        return await document_repository.get_by_user(db, user.id)

    async def get_document(self, db: AsyncSession, doc_id: uuid.UUID, user: User) -> GeneratedDocument:
        doc = await document_repository.get(db, doc_id)
        if not doc:
            raise NotFoundException("Document record not found")

        # Access check: Users can only read their own documents
        user_roles = [r.name for r in user.roles]
        if "Admin" not in user_roles and doc.user_id != user.id:
            raise ForbiddenException("Access restricted to creator of the document")
            
        return doc

    async def delete_document(self, db: AsyncSession, doc_id: uuid.UUID) -> GeneratedDocument:
        doc = await document_repository.get(db, doc_id)
        if not doc:
            raise NotFoundException("Document record not found")
            
        # Delete files from storage if not client-side logs
        if doc.html_path and doc.html_path != "client_side_draft":
            try:
                storage = get_storage()
                await storage.delete_file(doc.html_path)
            except Exception:
                pass
        if doc.pdf_path and doc.pdf_path != "client_side_draft":
            try:
                storage = get_storage()
                await storage.delete_file(doc.pdf_path)
            except Exception:
                pass

        return await document_repository.remove(db, id=doc_id)

    async def log_client_generation(
        self, db: AsyncSession, *, user: User, template_id: uuid.UUID, excel_file_name: str
    ) -> GeneratedDocument:
        from app.modules.templates.model import HtmlTemplate

        # Debug print
        print(f"[DEBUG_TOKEN] Received template_id: {template_id} (Type: {type(template_id)})")
        
        # List all templates in DB for debugging
        all_stmt = select(HtmlTemplate)
        all_res = await db.execute(all_stmt)
        all_tpls = all_res.scalars().all()
        for t in all_tpls:
            print(f"[DEBUG_TOKEN] DB Template: ID={t.id}, Name='{t.name}', is_active={t.is_active}, is_deleted={t.is_deleted}")

        # Resolve HTML template
        stmt = select(HtmlTemplate).where(HtmlTemplate.id == template_id, HtmlTemplate.is_deleted == False)
        res = await db.execute(stmt)
        tpl = res.scalar_one_or_none()
        if not tpl:
            raise NotFoundException("HTML template not found")

        user_roles = [r.name for r in user.roles]

        # Enforce Report Generation Limits for standard Users
        if "Admin" not in user_roles:
            count_stmt = select(func.count(GeneratedDocument.id)).where(
                and_(
                    GeneratedDocument.user_id == user.id,
                    GeneratedDocument.status == "Success"
                )
            )
            count_res = await db.execute(count_stmt)
            generated_count = count_res.scalar() or 0
            if generated_count >= user.report_limit:
                raise ForbiddenException(
                    f"You have reached your report generation quota limit of {user.report_limit} reports. "
                    "Please contact an administrator to increase your allocation limit."
                )

        # Log entry to DB (template_id set to None to avoid foreign key violation on document_templates)
        doc_in_data = {
            "user_id": user.id,
            "template_id": None,
            "name": f"{tpl.name.upper()}_Draft_{new_date_label()}",
            "excel_file_name": excel_file_name,
            "html_path": "client_side_draft",
            "pdf_path": None,
            "status": "Success",
            "execution_time_ms": 0
        }
        
        doc = await document_repository.create(db, obj_in_data=doc_in_data)
        return doc



document_service = DocumentService()


def new_date_label() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")
