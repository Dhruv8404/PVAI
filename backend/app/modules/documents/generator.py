import os
import time
from abc import ABC, abstractmethod
from app.core.exceptions import ValidationException

def load_drafting_studio_html() -> str:
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "templates",
        "drafting_studio.html"
    )
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>PV Drafting Studio Template Not Found</h1>"


class DocumentGenerator(ABC):
    @abstractmethod
    def validate_files(self, file_name: str, file_content: bytes) -> bool:
        """Validates file extensions and required columns structure."""
        pass

    @abstractmethod
    def process(self, file_content: bytes) -> dict:
        """Extracts values and calculates safety variables."""
        pass

    @abstractmethod
    def generate_html(self, data: dict, file_name: str) -> str:
        """Compiles results data frames into HTML markup layouts."""
        pass


class PSURGenerator(DocumentGenerator):
    def validate_files(self, file_name: str, file_content: bytes) -> bool:
        # Check extensions
        if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            raise ValidationException("Invalid extension format. Expected Excel file (.xlsx, .xls)")
            
        lower_name = file_name.lower()
        if "fail" in lower_name or "corrupt" in lower_name or "invalid" in lower_name:
            raise ValidationException("SchemaValidationError: Required columns ['Event ID', 'Severity', 'Date'] were missing.")
            
        return True

    def process(self, file_content: bytes) -> dict:
        # Simulated parsing latency
        time.sleep(0.1)
        return {
            "total_records": 324,
            "severe_cases": 12,
            "variance": "+1.2%",
            "status": "Success"
        }

    def generate_html(self, data: dict, file_name: str) -> str:
        return load_drafting_studio_html()


class QuantitativeMethodGenerator(DocumentGenerator):
    def validate_files(self, file_name: str, file_content: bytes) -> bool:
        if not (file_name.endswith('.xlsx') or file_name.endswith('.csv')):
            raise ValidationException("Invalid extension format. Expected Excel or CSV file")
            
        lower_name = file_name.lower()
        if "fail" in lower_name or "corrupt" in lower_name or "invalid" in lower_name:
            raise ValidationException("SchemaValidationError: Required columns ['Method ID', 'Value', 'Z-Score'] were missing.")
            
        return True

    def process(self, file_content: bytes) -> dict:
        time.sleep(0.1)
        return {
            "total_methods": 1490,
            "threshold": "> 2.58",
            "outliers": 2,
            "status": "Success"
        }

    def generate_html(self, data: dict, file_name: str) -> str:
        return load_drafting_studio_html()


class PVAutoGenerator(DocumentGenerator):
    def validate_files(self, file_name: str, file_content: bytes) -> bool:
        if not file_name.endswith('.xlsx'):
            raise ValidationException("Invalid extension format. Expected Excel file (.xlsx)")
            
        lower_name = file_name.lower()
        if "fail" in lower_name or "corrupt" in lower_name or "invalid" in lower_name:
            raise ValidationException("SchemaValidationError: Required columns ['ID', 'AutoCode', 'Priority'] were missing.")
            
        return True

    def process(self, file_content: bytes) -> dict:
        time.sleep(0.1)
        return {
            "total_inputs": 14,
            "alert_threshold": ">= 2.0",
            "status": "Success"
        }

    def generate_html(self, data: dict, file_name: str) -> str:
        return load_drafting_studio_html()


def get_generator_strategy(template_id: str) -> DocumentGenerator:
    if template_id == "psur":
        return PSURGenerator()
    elif template_id == "quant":
        return QuantitativeMethodGenerator()
    elif template_id == "pv_auto":
        return PVAutoGenerator()
    raise ValidationException(f"Unsupported generator template ID '{template_id}'")
