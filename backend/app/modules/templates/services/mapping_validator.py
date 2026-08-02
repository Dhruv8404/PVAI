import logging
from typing import List, Dict, Any
from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class MappingValidator:
    def validate_mappings(
        self, 
        mappings: List[Dict[str, Any]], 
        required_fields: List[str]
    ) -> None:
        """Validates mapping results for duplicates or logical conflicts.
        
        mappings format:
        [
            {
                "uploaded_header": "Subject",
                "mapped_field": "Patient Name",
                "expected_type": "PSUR Current"
            },
            ...
        ]
        """
        logger.info("Validating header mappings...")
        
        seen_uploaded = set()
        seen_mapped = set()
        
        for idx, item in enumerate(mappings):
            uploaded = item.get("uploaded_header")
            mapped = item.get("mapped_field")
            expected_type = item.get("expected_type", "")

            if not uploaded or not isinstance(uploaded, str):
                raise ValidationException(f"Invalid uploaded_header at index {idx}.")
            if not mapped or not isinstance(mapped, str):
                raise ValidationException(f"Invalid mapped_field at index {idx}.")

            # 1. Check duplicate uploaded headers mapping within the same expected file type
            key_uploaded = (expected_type, uploaded.strip().lower())
            if key_uploaded in seen_uploaded:
                raise ValidationException(f"Duplicate mapping defined for uploaded header '{uploaded}' in '{expected_type}'.")
            seen_uploaded.add(key_uploaded)

            # 2. Check duplicate target field mappings within the same expected file type
            key_mapped = (expected_type, mapped.strip().lower())
            if key_mapped in seen_mapped:
                raise ValidationException(f"Duplicate mapping target defined for field '{mapped}' in '{expected_type}'.")
            seen_mapped.add(key_mapped)

        # 3. Check for empty mappings list
        if not mappings:
            raise ValidationException("Mappings list cannot be empty.")


mapping_validator = MappingValidator()
