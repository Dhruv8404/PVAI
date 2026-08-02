import logging
from typing import List, Dict, Any
from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class TemplateMetadataService:
    ALLOWED_DATA_TYPES = {"string", "integer", "float", "date", "boolean", "enum"}

    def validate_manifest(self, manifest_data: Dict[str, Any]) -> None:
        """Validates the input template manifest structure and constraints.
        
        Raises:
            ValidationException: if validation constraints are violated.
        """
        if not isinstance(manifest_data, dict):
            raise ValidationException("Manifest must be a JSON object.")

        # 1. Validate required files list
        required_files = manifest_data.get("required_excel_files")
        if not required_files or not isinstance(required_files, list):
            raise ValidationException("Manifest must contain a non-empty 'required_excel_files' list.")
            
        # Check duplicate required excel files
        seen_files = set()
        for idx, file_label in enumerate(required_files):
            if not isinstance(file_label, str) or not file_label.strip():
                raise ValidationException(f"Excel file label at index {idx} must be a non-empty string.")
            
            clean_file = file_label.strip().lower()
            if clean_file in seen_files:
                raise ValidationException(f"Duplicate file label found in manifest required files: '{file_label}'.")
            seen_files.add(clean_file)

        # 2. Validate required fields list
        required_fields = manifest_data.get("required_fields")
        if not required_fields or not isinstance(required_fields, list):
            raise ValidationException("Manifest must contain a non-empty 'required_fields' list.")

        # Check duplicate fields and format
        seen_fields = set()
        for idx, field in enumerate(required_fields):
            if not isinstance(field, dict):
                raise ValidationException(f"Field configuration at index {idx} must be an object.")
                
            field_name = field.get("field_name")
            if not field_name or not isinstance(field_name, str) or not field_name.strip():
                raise ValidationException(f"Field configuration at index {idx} is missing a valid 'field_name'.")
            
            clean_name = field_name.strip().lower()
            if clean_name in seen_fields:
                raise ValidationException(f"Duplicate field name found in manifest required fields: '{field_name}'.")
            seen_fields.add(clean_name)
            
            # Validate data type
            data_type = field.get("data_type", "string")
            if not isinstance(data_type, str) or data_type.lower() not in self.ALLOWED_DATA_TYPES:
                raise ValidationException(
                    f"Invalid data_type '{data_type}' for field '{field_name}'. "
                    f"Must be one of: {', '.join(sorted(self.ALLOWED_DATA_TYPES))}"
                )

            # Validate examples type
            examples = field.get("examples")
            if examples is not None and not isinstance(examples, list):
                raise ValidationException(f"Field 'examples' for field '{field_name}' must be a list of strings.")

            # Validate aliases type
            aliases = field.get("aliases")
            if aliases is not None and not isinstance(aliases, list):
                raise ValidationException(f"Field 'aliases' for field '{field_name}' must be a list of strings.")


template_metadata_service = TemplateMetadataService()
