import os
import uuid
import shutil
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, BackgroundTasks

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.database import SessionLocal
from app.modules.templates.model import HtmlTemplate, TemplateField, AIConfiguration
from app.modules.templates.services.embedding_service import embedding_service
from app.modules.templates.services.template_metadata_service import template_metadata_service


logger = logging.getLogger(__name__)


# Background task runner for embedding generation
async def generate_embeddings_background_task(template_id: uuid.UUID):
    logger.info(f"[Background Embeddings] Starting vector generation for template {template_id}...")
    
    # Create a fresh database session for background work
    async with SessionLocal() as db:
        try:
            # 1. Fetch template and its fields
            stmt = select(HtmlTemplate).where(HtmlTemplate.id == template_id)
            res = await db.execute(stmt)
            template = res.scalar_one_or_none()
            
            if not template:
                logger.error(f"[Background Embeddings] Template {template_id} not found.")
                return

            stmt_fields = select(TemplateField).where(TemplateField.template_id == template_id)
            res_fields = await db.execute(stmt_fields)
            fields = res_fields.scalars().all()
            
            if not fields:
                logger.warning(f"[Background Embeddings] No fields found for template {template_id}. Marking Ready.")
                template.status = "Ready"
                await db.commit()
                return

            # 2. Iterate and generate vectors
            failed_any = False
            for field in fields:
                try:
                    logger.info(f"[Background Embeddings] Generating vector for '{field.field_name}'...")
                    vector = embedding_service.generate_embedding(field.field_name)
                    
                    # Store in ChromaDB
                    doc_id = embedding_service.store_field_embedding(
                        template_id=str(template_id),
                        field_name=field.field_name,
                        embedding=vector,
                        metadata={
                            "template_id": str(template_id),
                            "field_name": field.field_name,
                            "required": field.required
                        }
                    )
                    
                    field.chroma_document_id = doc_id
                    field.embedding_status = "Completed"
                    logger.info(f"[Background Embeddings] Stored successfully: '{field.field_name}' -> ID: {doc_id}")
                except Exception as ex:
                    logger.error(f"[Background Embeddings] Failed field '{field.field_name}': {ex}")
                    field.embedding_status = "Failed"
                    failed_any = True

            # 3. Resolve template final status
            if failed_any:
                logger.error(f"[Background Embeddings] Embedding generation failed for some fields in template {template_id}. Rolling back vector store...")
                template.status = "Failed"
                # Wipe any stored vectors in ChromaDB to prevent dirty states
                embedding_service.delete_template_embeddings(str(template_id))
            else:
                logger.info(f"[Background Embeddings] Successfully vectorized all fields for template {template_id}.")
                template.status = "Ready"
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"[Background Embeddings] Critical error in background thread: {e}")
            try:
                # Wiping vectors
                embedding_service.delete_template_embeddings(str(template_id))
                # Update status
                stmt_fail = (
                    update(HtmlTemplate)
                    .where(HtmlTemplate.id == template_id)
                    .values(status="Failed")
                )
                await db.execute(stmt_fail)
                await db.commit()
            except Exception as rollback_ex:
                logger.critical(f"[Background Embeddings] Double fault during cleanup: {rollback_ex}")


class TemplateService:
    async def list_templates(self, db: AsyncSession) -> List[HtmlTemplate]:
        """Lists all templates that are not soft-deleted."""
        stmt = select(HtmlTemplate).where(HtmlTemplate.is_deleted == False).order_by(HtmlTemplate.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_template(self, db: AsyncSession, template_id: uuid.UUID) -> HtmlTemplate:
        """Gets template detail. Raises NotFoundException if not exists."""
        stmt = select(HtmlTemplate).where(HtmlTemplate.id == template_id, HtmlTemplate.is_deleted == False)
        res = await db.execute(stmt)
        tpl = res.scalar_one_or_none()
        if not tpl:
            raise NotFoundException("HTML template not found")
        return tpl

    async def create_template_draft(
        self, 
        db: AsyncSession, 
        file: UploadFile, 
        name: str, 
        version: str, 
        description: Optional[str],
        uploaded_by: Optional[str]
    ) -> HtmlTemplate:
        """Step 1: Upload template draft."""
        # 1. Validation: Name & Version uniqueness
        stmt_dup = select(HtmlTemplate).where(
            and_(
                HtmlTemplate.name == name.strip(),
                HtmlTemplate.version == version.strip(),
                HtmlTemplate.is_deleted == False
            )
        )
        res_dup = await db.execute(stmt_dup)
        if res_dup.scalar_one_or_none():
            raise ValidationException("A template with this name and version already exists.")

        # 2. File Format Check
        if not file.filename or not file.filename.lower().endswith(".html"):
            raise ValidationException("Only HTML files (.html) are allowed.")

        # 3. File Size Check (5MB)
        max_size = 5 * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            raise ValidationException("HTML template file size exceeds 5MB limit.")
        await file.seek(0)

        # Validate basic HTML structure
        html_str = content.decode("utf-8", errors="ignore")
        if "<html" not in html_str.lower() and "<body" not in html_str.lower():
            raise ValidationException("Invalid HTML file structure. Root elements missing.")

        # 4. Save template file
        # 4. Save template file using unified storage provider
        import tempfile
        os.makedirs("storage/temp", exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(dir="storage/temp", suffix=".html")
        try:
            with os.fdopen(temp_fd, 'wb') as tmp:
                tmp.write(content)
            
            from app.core.storage import StorageProviderFactory
            provider = StorageProviderFactory.get_provider()
            dest_name = f"{uuid.uuid4().hex}.html"
            filepath = provider.upload_file(temp_path, dest_name)
        except Exception as e:
            raise ValidationException(f"Failed to upload template to storage provider: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # 5. Create Draft record
        new_tpl = HtmlTemplate(
            name=name.strip(),
            version=version.strip(),
            description=description.strip() if description else None,
            html_file=filepath,
            is_active=False,
            is_deleted=False,
            uploaded_by=uploaded_by,
            status="Draft"
        )
        db.add(new_tpl)
        await db.commit()
        await db.refresh(new_tpl)
        
        logger.info(f"Template draft '{new_tpl.name}' (v{new_tpl.version}) uploaded successfully. ID: {new_tpl.id}")
        return new_tpl

    async def submit_template_manifest(
        self, 
        db: AsyncSession, 
        template_id: uuid.UUID, 
        required_excel_files: List[str], 
        required_fields: List[Dict[str, Any]],
        background_tasks: BackgroundTasks
    ) -> HtmlTemplate:
        """Step 2: Submit manifest configuration, create fields, and queue async embedding task."""
        # 1. Fetch draft template
        tpl = await self.get_template(db, template_id)
        if tpl.status not in ("Draft", "Failed"):
            raise ValidationException(f"Cannot submit manifest for template in '{tpl.status}' status.")

        # 2. Validate manifest inputs
        manifest_payload = {
            "required_excel_files": required_excel_files,
            "required_fields": required_fields
        }
        template_metadata_service.validate_manifest(manifest_payload)

        # 3. Clean existing fields if failed retry
        stmt_del = select(TemplateField).where(TemplateField.template_id == template_id)
        res_del = await db.execute(stmt_del)
        old_fields = res_del.scalars().all()
        for f in old_fields:
            await db.delete(f)

        # 4. Save manifest details & status to "Processing"
        tpl.required_files = required_excel_files
        tpl.status = "Processing"

        # Create new fields in DB (status Pending)
        for field_data in required_fields:
            new_field = TemplateField(
                template_id=template_id,
                field_name=field_data["field_name"].strip(),
                description=field_data.get("description", "").strip() or None,
                required=field_data.get("required", True),
                data_type=field_data.get("data_type", "string").lower(),
                examples=field_data.get("examples", []),
                aliases=field_data.get("aliases", []),
                embedding_status="Pending"
            )
            db.add(new_field)

        await db.commit()
        await db.refresh(tpl)

        # 5. Delegate embedding vectorization to background task
        background_tasks.add_task(generate_embeddings_background_task, template_id)
        
        logger.info(f"Manifest submitted for template '{tpl.name}'. Background embedding task queued.")
        return tpl

    async def update_template_status(self, db: AsyncSession, template_id: uuid.UUID, is_active: bool) -> HtmlTemplate:
        """Activates or deactivates a template. Only templates in 'Ready' status can be activated."""
        tpl = await self.get_template(db, template_id)
        
        if is_active:
            if tpl.status != "Ready" and tpl.status != "Inactive":
                raise ValidationException(f"Only templates in 'Ready' or 'Inactive' status can be activated. Current status: '{tpl.status}'")
            
            # Deactivate all other templates
            await db.execute(
                update(HtmlTemplate)
                .where(and_(HtmlTemplate.id != template_id, HtmlTemplate.is_deleted == False))
                .values(is_active=False, status="Inactive")
            )
            tpl.is_active = True
            tpl.status = "Active"
            logger.info(f"Template '{tpl.name}' activated.")
        else:
            tpl.is_active = False
            tpl.status = "Inactive"
            logger.info(f"Template '{tpl.name}' deactivated.")
            
        await db.commit()
        await db.refresh(tpl)
        return tpl

    async def delete_template(self, db: AsyncSession, template_id: uuid.UUID) -> None:
        """Soft deletes a template and wipes its vectors in ChromaDB."""
        tpl = await self.get_template(db, template_id)
        
        tpl.is_deleted = True
        tpl.is_active = False
        tpl.status = "Inactive"
        
        # Remove from ChromaDB vector store
        embedding_service.delete_template_embeddings(str(template_id))
        
        await db.commit()
        logger.info(f"Template '{tpl.name}' soft deleted and vectors purged.")

    async def get_ai_config(self, db: AsyncSession) -> AIConfiguration:
        """Retrieves current AI configuration. Seeds default if none exists."""
        stmt = select(AIConfiguration)
        res = await db.execute(stmt)
        config = res.scalars().first()
        if not config:
            config = AIConfiguration()
            db.add(config)
            await db.commit()
            await db.refresh(config)
        return config

    async def update_ai_config(self, db: AsyncSession, update_data: Dict[str, Any]) -> AIConfiguration:
        """Updates the singleton AIConfiguration settings."""
        config = await self.get_ai_config(db)
        for key, val in update_data.items():
            if hasattr(config, key) and key not in ("id", "created_at", "updated_at"):
                setattr(config, key, val)
        config.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(config)
        logger.info("AIConfiguration updated successfully.")
        return config


template_service = TemplateService()
