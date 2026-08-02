import os
import logging
import threading
import uuid
import math
import hashlib
from typing import List, Dict, Any, Optional

from django.db import transaction
from django.core.exceptions import ValidationError

from .models import HtmlTemplate, TemplateField, AIConfiguration

logger = logging.getLogger(__name__)

# Fallback libraries for environments without ChromaDB or SentenceTransformers
HAS_SENTENCE_TRANSFORMERS = False
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    logger.warning("sentence-transformers not installed. Mock embeddings will be used.")

HAS_CHROMADB = False
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    logger.warning("chromadb not installed. In-memory dictionary mock will be used.")


class EmbeddingService:
    def __init__(self, persist_directory: str = "storage/chromadb"):
        self.persist_directory = persist_directory
        self._model = None
        self._chroma_client = None
        self._collection = None
        self._mock_db = {}
        os.makedirs(self.persist_directory, exist_ok=True)

    def _get_model(self):
        if self._model is None and HAS_SENTENCE_TRANSFORMERS:
            try:
                self._model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            except Exception as e:
                logger.error(f"Failed to load sentence-transformer model: {e}")
        return self._model

    def _get_chroma_client(self):
        if self._chroma_client is None and HAS_CHROMADB:
            try:
                self._chroma_client = chromadb.PersistentClient(path=self.persist_directory)
            except Exception as e:
                logger.error(f"Failed to init ChromaDB client: {e}")
        return self._chroma_client

    def _get_collection(self):
        client = self._get_chroma_client()
        if client:
            try:
                self._collection = client.get_or_create_collection(name="template_fields")
                return self._collection
            except Exception as e:
                logger.error(f"Failed to create ChromaDB collection: {e}")
        return None

    def generate_embedding(self, text: str) -> List[float]:
        model = self._get_model()
        if model:
            try:
                embeddings = model.encode([text], normalize_embeddings=True)
                return [float(x) for x in embeddings[0]]
            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")

        # Deterministic Mock Fallback (384-dimensional)
        sha = hashlib.sha256(text.encode("utf-8")).digest()
        result = []
        for i in range(384):
            val = sha[(i % len(sha))] * ((i + 1) * 0.13)
            result.append(float(math.sin(val)))
        return result

    def store_field_embedding(self, template_id: str, field_name: str, embedding: List[float], metadata: Dict[str, Any]) -> str:
        doc_id = f"{template_id}_{field_name.replace(' ', '_')}"
        collection = self._get_collection()
        if collection:
            try:
                collection.upsert(
                    ids=[doc_id],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    documents=[field_name]
                )
                return doc_id
            except Exception as e:
                logger.error(f"ChromaDB upsert failed: {e}")

        self._mock_db[doc_id] = {
            "template_id": template_id,
            "field_name": field_name,
            "embedding": embedding,
            "metadata": metadata
        }
        return doc_id

    def delete_template_embeddings(self, template_id: str) -> None:
        collection = self._get_collection()
        template_id_str = str(template_id)
        if collection:
            try:
                collection.delete(where={"template_id": template_id_str})
                return
            except Exception as e:
                logger.error(f"ChromaDB delete failed: {e}")

        keys_to_delete = [k for k, v in self._mock_db.items() if str(v.get("template_id")) == template_id_str]
        for k in keys_to_delete:
            del self._mock_db[k]


embedding_service = EmbeddingService()


class TemplateMetadataService:
    ALLOWED_DATA_TYPES = {"string", "integer", "float", "date", "boolean", "enum"}

    def validate_manifest(self, manifest_data: Dict[str, Any]) -> None:
        required_files = manifest_data.get("required_excel_files")
        if not required_files or not isinstance(required_files, list):
            raise ValidationError("Manifest must contain a non-empty 'required_excel_files' list.")

        seen_files = set()
        for f in required_files:
            if not isinstance(f, str) or not f.strip():
                raise ValidationError("Excel file labels must be non-empty strings.")
            clean_f = f.strip().lower()
            if clean_f in seen_files:
                raise ValidationError(f"Duplicate file label: '{f}'")
            seen_files.add(clean_f)

        required_fields = manifest_data.get("required_fields")
        if not required_fields or not isinstance(required_fields, list):
            raise ValidationError("Manifest must contain a non-empty 'required_fields' list.")

        seen_fields = set()
        for field in required_fields:
            if not isinstance(field, dict):
                raise ValidationError("Field configuration must be an object.")
            name = field.get("field_name")
            if not name or not isinstance(name, str) or not name.strip():
                raise ValidationError("Field configurations must contain 'field_name'.")
            
            clean_name = name.strip().lower()
            if clean_name in seen_fields:
                raise ValidationError(f"Duplicate field name: '{name}'")
            seen_fields.add(clean_name)

            data_type = field.get("data_type", "string")
            if data_type.lower() not in self.ALLOWED_DATA_TYPES:
                raise ValidationError(f"Invalid data_type: '{data_type}'. Allowed: {self.ALLOWED_DATA_TYPES}")


template_metadata_service = TemplateMetadataService()


def run_async_embeddings(template_id: uuid.UUID):
    """Executes the asynchronous background embedding generation task."""
    try:
        template = HtmlTemplate.objects.get(id=template_id)
        fields = template.fields.all()
        
        failed_any = False
        for field in fields:
            try:
                vector = embedding_service.generate_embedding(field.field_name)
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
                field.embedding_status = 'Completed'
                field.save()
            except Exception as ex:
                logger.error(f"Failed to generate embedding for field '{field.field_name}': {ex}")
                field.embedding_status = 'Failed'
                field.save()
                failed_any = True

        if failed_any:
            template.status = 'Failed'
            embedding_service.delete_template_embeddings(str(template_id))
        else:
            template.status = 'Ready'
        template.save()

    except Exception as e:
        logger.error(f"Background embedding error: {e}")
        try:
            HtmlTemplate.objects.filter(id=template_id).update(status='Failed')
            embedding_service.delete_template_embeddings(str(template_id))
        except Exception:
            pass


class TemplateService:
    def create_template_draft(self, name: str, version: str, description: Optional[str], html_file_path: str, uploaded_by: Optional[str]) -> HtmlTemplate:
        # Check duplicate name/version
        if HtmlTemplate.objects.filter(name=name.strip(), version=version.strip(), is_deleted=False).exists():
            raise ValidationError("A template with this name and version already exists.")

        template = HtmlTemplate.objects.create(
            name=name.strip(),
            version=version.strip(),
            description=description,
            html_file=html_file_path,
            uploaded_by=uploaded_by,
            status='Draft'
        )
        return template

    def submit_template_manifest(self, template_id: uuid.UUID, required_excel_files: List[str], required_fields: List[Dict[str, Any]]) -> HtmlTemplate:
        with transaction.atomic():
            template = HtmlTemplate.objects.select_for_update().get(id=template_id, is_deleted=False)
            if template.status not in ('Draft', 'Failed'):
                raise ValidationError(f"Cannot submit manifest in current state: '{template.status}'")

            # Validate input data
            manifest_payload = {
                "required_excel_files": required_excel_files,
                "required_fields": required_fields
            }
            template_metadata_service.validate_manifest(manifest_payload)

            # Clean old fields
            template.fields.all().delete()

            # Save manifest files
            template.required_files = required_excel_files
            template.status = 'Processing'
            template.save()

            # Create field records
            for field in required_fields:
                TemplateField.objects.create(
                    template=template,
                    field_name=field["field_name"].strip(),
                    description=field.get("description"),
                    required=field.get("required", True),
                    data_type=field.get("data_type", "string").lower(),
                    examples=field.get("examples", []),
                    aliases=field.get("aliases", []),
                    embedding_status='Pending'
                )

        # Kick off background job
        thread = threading.Thread(target=run_async_embeddings, args=(template.id,))
        thread.daemon = True
        thread.start()

        return template

    def update_template_status(self, template_id: uuid.UUID, is_active: bool) -> HtmlTemplate:
        with transaction.atomic():
            template = HtmlTemplate.objects.select_for_update().get(id=template_id, is_deleted=False)
            if is_active:
                if template.status not in ('Ready', 'Inactive'):
                    raise ValidationError("Only 'Ready' or 'Inactive' templates can be activated.")
                
                # Deactivate all others
                HtmlTemplate.objects.filter(is_deleted=False).exclude(id=template_id).update(
                    is_active=False, status='Inactive'
                )
                template.is_active = True
                template.status = 'Active'
            else:
                template.is_active = False
                template.status = 'Inactive'
            template.save()
        return template

    def delete_template(self, template_id: uuid.UUID) -> None:
        with transaction.atomic():
            template = HtmlTemplate.objects.select_for_update().get(id=template_id, is_deleted=False)
            template.is_deleted = True
            template.is_active = False
            template.status = 'Inactive'
            template.save()

            # Delete ChromaDB embeddings
            embedding_service.delete_template_embeddings(str(template_id))

    def get_ai_config(self) -> AIConfiguration:
        config, _ = AIConfiguration.objects.get_or_create(id=uuid.UUID('00000000-0000-0000-0000-000000000000'))
        return config

    def update_ai_config(self, update_data: Dict[str, Any]) -> AIConfiguration:
        config = self.get_ai_config()
        for k, v in update_data.items():
            if hasattr(config, k) and k not in ('id', 'created_at', 'updated_at'):
                setattr(config, k, v)
        config.save()
        return config


template_service = TemplateService()
