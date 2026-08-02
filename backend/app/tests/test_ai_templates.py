import os
import sys
import uuid
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend app folder to path for import safety
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.exceptions import ValidationException, NotFoundException
from app.modules.templates.model import HtmlTemplate, TemplateField, AIConfiguration
from app.modules.templates.services.embedding_service import embedding_service
from app.modules.templates.services.template_metadata_service import template_metadata_service
from app.modules.templates.services.template_service import template_service, generate_embeddings_background_task


class TestEmbeddingService(unittest.TestCase):
    def test_embedding_generation_dimension(self):
        """Verify vector generated is 384-dimensional."""
        vector = embedding_service.generate_embedding("Patient Name")
        self.assertEqual(len(vector), 384)
        self.assertTrue(all(isinstance(x, float) for x in vector))

    def test_store_and_delete_embeddings(self):
        """Test storing and deleting embeddings inside the service."""
        template_id = str(uuid.uuid4())
        field_name = "Patient Name"
        embedding = embedding_service.generate_embedding(field_name)
        
        doc_id = embedding_service.store_field_embedding(
            template_id=template_id,
            field_name=field_name,
            embedding=embedding,
            metadata={"template_id": template_id, "required": True}
        )
        
        self.assertTrue(doc_id.startswith(template_id))
        
        # Test clean up
        embedding_service.delete_template_embeddings(template_id)


class TestTemplateMetadataService(unittest.TestCase):
    def test_valid_manifest(self):
        """Assert valid manifest passes without exception."""
        valid_manifest = {
            "required_excel_files": ["PSUR Current", "ES Current"],
            "required_fields": [
                {"field_name": "Patient Name", "data_type": "string", "required": True},
                {"field_name": "Age", "data_type": "integer", "required": False}
            ]
        }
        try:
            template_metadata_service.validate_manifest(valid_manifest)
        except ValidationException:
            self.fail("validate_manifest raised ValidationException unexpectedly on valid manifest.")

    def test_duplicate_files(self):
        """Assert duplicate files in manifest raise ValidationException."""
        invalid_manifest = {
            "required_excel_files": ["PSUR Current", "PSUR Current"],
            "required_fields": [
                {"field_name": "Patient Name", "data_type": "string"}
            ]
        }
        with self.assertRaises(ValidationException) as ctx:
            template_metadata_service.validate_manifest(invalid_manifest)
        self.assertIn("Duplicate file label", str(ctx.exception))

    def test_duplicate_fields(self):
        """Assert duplicate fields in manifest raise ValidationException."""
        invalid_manifest = {
            "required_excel_files": ["PSUR Current"],
            "required_fields": [
                {"field_name": "Patient Name", "data_type": "string"},
                {"field_name": "patient name", "data_type": "string"}
            ]
        }
        with self.assertRaises(ValidationException) as ctx:
            template_metadata_service.validate_manifest(invalid_manifest)
        self.assertIn("Duplicate field name", str(ctx.exception))

    def test_invalid_datatype(self):
        """Assert invalid data_type in manifest raises ValidationException."""
        invalid_manifest = {
            "required_excel_files": ["PSUR Current"],
            "required_fields": [
                {"field_name": "Patient Name", "data_type": "unsupported_type"}
            ]
        }
        with self.assertRaises(ValidationException) as ctx:
            template_metadata_service.validate_manifest(invalid_manifest)
        self.assertIn("Invalid data_type", str(ctx.exception))


class TestTemplateServiceAsync(unittest.IsolatedAsyncioTestCase):
    async def test_submit_manifest_draft_validation(self):
        """Verify manifest submission is rejected if template is not in Draft/Failed status."""
        mock_db = AsyncMock()
        
        # Mock HTML Template not in draft state
        active_template = HtmlTemplate(
            id=uuid.uuid4(),
            name="Active Template",
            status="Active"
        )
        
        with patch.object(template_service, "get_template", return_value=active_template):
            with self.assertRaises(ValidationException) as ctx:
                await template_service.submit_template_manifest(
                    db=mock_db,
                    template_id=active_template.id,
                    required_excel_files=["PSUR Current"],
                    required_fields=[{"field_name": "Patient Name", "data_type": "string"}],
                    background_tasks=MagicMock()
                )
            self.assertIn("Cannot submit manifest for template", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
