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
from app.modules.templates.model import TemplateField
from app.modules.templates.services.excel_data_service import excel_data_service
from app.modules.templates.services.data_standardization_service import data_standardization_service, parse_iso_date
from app.modules.templates.services.file_merge_service import file_merge_service
from app.modules.templates.services.validation_service import validation_service
from app.modules.templates.services.dataset_builder_service import dataset_builder_service


def create_mock_excel_data(headers: list, rows_data: list, sheet_name: str = "Sheet1") -> bytes:
    """Helper to generate a mock spreadsheet in memory with data rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows_data:
        ws.append(row)
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


class TestExcelDataService(unittest.TestCase):
    def test_row_extraction_and_provenance(self):
        """Verify headers map to logical fields and _source metadata matches."""
        headers = ["Subject", "Years", "Reaction Preferred Term"]
        rows_data = [
            ["Subject001", 45, "Headache"],
            ["Subject002", 30, "Nausea"]
        ]
        excel_bytes = create_mock_excel_data(headers, rows_data, "Cases")
        
        mappings = {
            "Subject": "Patient Name",
            "Years": "Age",
            "Reaction Preferred Term": "PT Name"
        }
        
        extracted = excel_data_service.extract_rows(excel_bytes, "PSUR Current.xlsx", "PSUR Current", mappings)
        self.assertEqual(len(extracted), 2)
        
        # Test first row logical fields mapping
        self.assertEqual(extracted[0]["Patient Name"], "Subject001")
        self.assertEqual(extracted[0]["Age"], 45)
        self.assertEqual(extracted[0]["PT Name"], "Headache")
        
        # Test provenance trace
        src = extracted[0]["_source"]
        self.assertEqual(src["file"], "PSUR Current.xlsx")
        self.assertEqual(src["sheet"], "Cases")
        self.assertEqual(src["row"], 2)  # Excel row 2 (row 1 is header)


class TestDataStandardizationService(unittest.TestCase):
    def test_date_parser(self):
        """Verify date parsing formats standardise to YYYY-MM-DD."""
        import datetime
        self.assertEqual(parse_iso_date("2026-07-10"), "2026-07-10")
        self.assertEqual(parse_iso_date("10-07-2026"), "2026-07-10")
        self.assertEqual(parse_iso_date("07/10/2026"), "2026-07-10")
        self.assertEqual(parse_iso_date(datetime.date(2026, 7, 10)), "2026-07-10")
        # Excel float date serial representation for 2026-07-10
        self.assertEqual(parse_iso_date(46213), "2026-07-10")


    def test_standardize_row(self):
        """Verify standardization formats values correctly and flags errors/warnings."""
        fields_config = {
            "Patient Name": TemplateField(field_name="Patient Name", data_type="string", required=True),
            "Age": TemplateField(field_name="Age", data_type="integer", required=False),
            "Created Date": TemplateField(field_name="Created Date", data_type="date", required=False),
            "Listedness": TemplateField(field_name="Listedness", data_type="enum", required=False, examples=["Listed", "Unlisted"])
        }
        
        raw_row = {
            "Patient Name": "  Subject001  ",
            "Age": "45.0",
            "Created Date": "10-07-2026",
            "Listedness": "listed",
            "_source": {"file": "f.xlsx", "sheet": "s", "row": 2}
        }
        
        standardized, issues = data_standardization_service.standardize_row(raw_row, fields_config)
        self.assertEqual(standardized["Patient Name"], "Subject001")  # whitespace trimmed
        self.assertEqual(standardized["Age"], 45)  # parsed float-to-int decimal stripping
        self.assertEqual(standardized["Created Date"], "2026-07-10")  # ISO standard date
        self.assertEqual(standardized["Listedness"], "Listed")  # matched enum case variant
        self.assertEqual(len(issues), 0)


class TestFileMergeService(unittest.TestCase):
    def test_merge_datasets(self):
        """Verify rows group under expected file labels."""
        rows1 = [{"Patient Name": "John"}]
        rows2 = [{"Patient Name": "Mary"}]
        
        datasets = [
            ("PSUR Current", rows1),
            ("ES Current", rows2)
        ]
        
        merged = file_merge_service.merge_datasets(datasets)
        self.assertIn("PSUR Current", merged)
        self.assertIn("ES Current", merged)
        self.assertEqual(merged["PSUR Current"]["rows"], rows1)
        self.assertEqual(merged["ES Current"]["rows"], rows2)


class TestValidationService(unittest.TestCase):
    def test_required_validation_and_duplicates(self):
        """Verify that required errors and duplicate case warnings trigger."""
        fields_config = {
            "Patient Name": TemplateField(field_name="Patient Name", data_type="string", required=True),
            "Report ID": TemplateField(field_name="Report ID", data_type="string", required=False)
        }
        
        merged_files = {
            "PSUR Current": {
                "rows": [
                    {
                        "Patient Name": None,  # missing required
                        "Report ID": "CASE001",
                        "_source": {"file": "f.xlsx", "sheet": "s", "row": 2}
                    },
                    {
                        "Patient Name": "Mary",
                        "Report ID": "CASE001",  # duplicate ID
                        "_source": {"file": "f.xlsx", "sheet": "s", "row": 3}
                    }
                ]
            }
        }
        
        logs, stats = validation_service.validate_dataset(merged_files, fields_config, [])
        self.assertEqual(stats["rows_processed"], 2)
        self.assertEqual(stats["errors"], 1)  # Patient Name missing
        self.assertEqual(stats["warnings"], 1)  # CASE001 duplicate
        
        # Verify severity
        self.assertEqual(logs[0]["severity"], "Error")
        self.assertEqual(logs[1]["severity"], "Warning")


class TestDatasetBuilderService(unittest.TestCase):
    def test_builder(self):
        """Verify JSON payload outputs coordinates correctly."""
        merged = {"PSUR Current": {"rows": []}}
        stats = {"total_rows": 0}
        
        payload = dataset_builder_service.build_standardized_payload(
            merged_files=merged,
            statistics=stats,
            template_id="tpl-uuid",
            customer_id="cust-123",
            dataset_version=2,
            processing_time_ms=150
        )
        
        self.assertEqual(payload["metadata"]["dataset_version"], 2)
        self.assertEqual(payload["metadata"]["customer_id"], "cust-123")
        self.assertEqual(payload["global_statistics"]["processing_time_ms"], 150)
        self.assertEqual(payload["files"], merged)


if __name__ == "__main__":
    unittest.main()
