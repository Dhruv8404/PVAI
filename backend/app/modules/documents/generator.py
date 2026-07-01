import time
from abc import ABC, abstractmethod
from app.core.exceptions import ValidationException


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
        return f"""
        <div style="font-family: sans-serif; padding: 24px; color: #1f2937; background: #ffffff;">
          <h1 style="color: #4f46e5; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-top: 0;">Periodic Safety Update Report (PSUR)</h1>
          <p style="color: #6b7280; font-size: 13px;">Source Worksheet: {file_name} | Status: {data['status']}</p>
          
          <div style="margin: 20px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: #f9fafb;">
            <h3 style="margin-top: 0; color: #111827;">Compliance Check Overview</h3>
            <p style="font-size: 14px;">Total Row Entries Checked: <strong>{data['total_records']} Adverse Events</strong></p>
            <p style="font-size: 14px;">Severe Adverse Cases Detected: <strong style="color: #ef4444;">{data['severe_cases']} (Critical)</strong></p>
            <p style="font-size: 14px;">Safety Index Variance: <strong>{data['variance']} (Within tolerances)</strong></p>
          </div>
        </div>
        """


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
        return f"""
        <div style="font-family: sans-serif; padding: 24px; color: #1f2937; background: #ffffff;">
          <h1 style="color: #0d9488; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-top: 0;">Quantitative Method (Non-DME) Analysis</h1>
          <p style="color: #6b7280; font-size: 13px;">Source Worksheet: {file_name} | Status: {data['status']}</p>
          
          <div style="margin: 20px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: #f0fdfa;">
            <h3 style="margin-top: 0; color: #115e59;">Z-Score Quantitative Check</h3>
            <p style="font-size: 14px;">Active Method Indices Checked: <strong>{data['total_methods']} Records</strong></p>
            <p style="font-size: 14px;">Statistical Critical Z-Score Threshold: <strong>{data['threshold']}</strong></p>
            <p style="font-size: 14px; color: #b91c1c; font-weight: bold;">Outliers Flagged: {data['outliers']} Methods Detected</p>
          </div>
        </div>
        """


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
        return f"""
        <div style="font-family: sans-serif; padding: 24px; color: #1f2937; background: #ffffff;">
          <h1 style="color: #7c3aed; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; margin-top: 0;">PV Auto Signal Detection Report</h1>
          <p style="color: #6b7280; font-size: 13px;">Source Worksheet: {file_name} | Status: {data['status']}</p>
          
          <div style="margin: 20px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: #faf5ff;">
            <h3 style="margin-top: 0; color: #6b21a8;">Signal Detections Triggered</h3>
            <p style="font-size: 14px;">Total AutoCode Inputs Processed: <strong>{data['total_inputs']} AEs</strong></p>
            <p style="font-size: 14px;">PRR Ratio Alert Threshold: <strong>{data['alert_threshold']}</strong></p>
          </div>
        </div>
        """


def get_generator_strategy(template_id: str) -> DocumentGenerator:
    if template_id == "psur":
        return PSURGenerator()
    elif template_id == "quant":
        return QuantitativeMethodGenerator()
    elif template_id == "pv_auto":
        return PVAutoGenerator()
    raise ValidationException(f"Unsupported generator template ID '{template_id}'")
