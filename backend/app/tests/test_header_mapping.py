import os
import sys
import uuid
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
import openpyxl

# Add backend app folder to path for import safety
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.exceptions import ValidationException
from app.modules.templates.model import HtmlTemplate, AIConfiguration
from app.modules.templates.services.excel_header_service import excel_header_service
from app.modules.templates.services.header_embedding_service import header_embedding_service
from app.modules.templates.services.header_similarity_service import header_similarity_service, compute_cosine_similarity
from app.modules.templates.services.llm_mapping_service import llm_mapping_service
from app.modules.templates.services.mapping_cache_service import mapping_cache_service
from app.modules.templates.services.header_mapping_coordinator import header_mapping_coordinator


def create_mock_excel(headers: list, sheet_name: str = "Sheet1") -> bytes:
    """Helper to generate a mock spreadsheet in memory."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


class TestExcelHeaderService(unittest.TestCase):
    def test_header_extraction(self):
        """Verify sheet names, column index, and header strings are extracted correctly."""
        headers = ["Subject", "Years", "Reaction Description"]
        excel_bytes = create_mock_excel(headers, "Cases")
        
        extracted = excel_header_service.extract_headers(excel_bytes, "PSUR Current.xlsx")
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["sheet_name"], "Cases")
        self.assertEqual(extracted[0]["file_name"], "PSUR Current.xlsx")
        
        headers_list = extracted[0]["headers"]
        self.assertEqual(len(headers_list), 3)
        self.assertEqual(headers_list[0]["column_index"], 1)
        self.assertEqual(headers_list[0]["original_header"], "Subject")
        self.assertEqual(headers_list[1]["column_index"], 2)
        self.assertEqual(headers_list[1]["original_header"], "Years")


class TestHeaderEmbeddingService(unittest.TestCase):
    def test_embedding_wrapper(self):
        """Verify vector generated is 384 float dimensions."""
        vector = header_embedding_service.generate_header_embedding("Years")
        self.assertEqual(len(vector), 384)


class TestHeaderSimilarityService(unittest.TestCase):
    def test_cosine_similarity(self):
        """Test cosine math helper."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(compute_cosine_similarity(v1, v2), 1.0)
        
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(compute_cosine_similarity(v1, v3), 0.0)

    def test_similarity_classification(self):
        """Verify threshold matching classifications function correctly."""
        ai_config = AIConfiguration(
            similarity_threshold=0.90,
            llm_threshold=0.70
        )
        
        # Test case: exact match (similarity = 1.0)
        matches = [("Patient Name", 1.0, True)]
        
        with patch.object(header_similarity_service, "find_nearest_fields") as mock_find:
            mock_find.return_value = [{
                "field_name": "Patient Name",
                "similarity": 1.0,
                "required": True,
                "status": "AutoMapped",
                "source": "Embedding"
            }]
            
            nearest = header_similarity_service.find_nearest_fields(
                template_id=uuid.uuid4(),
                header_name="Patient Name",
                header_embedding=[0.1]*384,
                ai_config=ai_config
            )
            self.assertEqual(nearest[0]["status"], "AutoMapped")
            self.assertEqual(nearest[0]["source"], "Embedding")


class TestLLMMappingService(unittest.TestCase):
    def test_fallback_mock_mapping(self):
        """Verify that rules-based string mapping aligns keys properly."""
        required = ["Patient Name", "Age", "PT Name"]
        uploaded = ["Subject", "Years", "Reaction Preferred Term", "Random Header"]
        
        mapping = llm_mapping_service._mock_similarity_mapping(required, uploaded)
        self.assertEqual(mapping.get("Patient Name"), "Subject")
        self.assertEqual(mapping.get("Age"), "Years")


class TestHeaderMappingCoordinator(unittest.TestCase):
    def test_match_file_to_expected_type(self):
        """Verify uploaded filenames match expectations."""
        required = ["PSUR Current", "ES Current", "SMQ"]
        
        type1 = asyncio_run_helper(header_mapping_coordinator.match_file_to_expected_type("accord_psur_current.xlsx", required))
        self.assertEqual(type1, "PSUR Current")
        
        type2 = asyncio_run_helper(header_mapping_coordinator.match_file_to_expected_type("es_current_v2.xlsx", required))
        self.assertEqual(type2, "ES Current")


def asyncio_run_helper(coro):
    """Helper to run async coroutines in tests."""
    return asyncio.run(coro)



import asyncio
if __name__ == "__main__":
    unittest.main()
