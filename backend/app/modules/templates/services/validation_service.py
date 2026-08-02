import logging
from typing import List, Dict, Any, Tuple
from app.modules.templates.model import TemplateField

logger = logging.getLogger(__name__)


class ValidationService:
    def validate_dataset(
        self, 
        merged_files: Dict[str, Any], 
        fields_config: Dict[str, TemplateField],
        standardization_issues: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Validates all merged records for required fields, type violations, and duplicates.
        
        Returns a tuple: (validation_logs, statistics_dict)
        """
        logger.info("Starting validation checks on merged dataset...")
        validation_logs = []
        
        # 1. Add issues discovered during standardization (provenance already attached)
        for issue in standardization_issues:
            source = issue.get("_source", {})
            validation_logs.append({
                "file_name": source.get("file"),
                "sheet_name": source.get("sheet"),
                "row_number": source.get("row"),
                "field_name": issue.get("field_name"),
                "message": issue.get("message"),
                "severity": issue.get("severity", "Error")
            })

        total_rows_count = 0
        invalid_rows_set = set()  # Tracks (file, sheet, row) that fail critical checks
        
        # 2. Check for missing required fields and duplicates
        for expected_type, file_data in merged_files.items():
            rows = file_data.get("rows", [])
            total_rows_count += len(rows)
            
            # Find potential ID field for duplicate checks (first field containing 'id' case-insensitively)
            id_field = None
            for field_name in fields_config.keys():
                fn_lower = field_name.lower()
                if "id" in fn_lower or fn_lower == "id" or fn_lower == "key":
                    id_field = field_name
                    break
            
            seen_ids = {} # {id_val: (file, sheet, row)}
            
            for row in rows:
                source = row.get("_source", {})
                file_name = source.get("file")
                sheet_name = source.get("sheet")
                row_num = source.get("row")
                row_key = (file_name, sheet_name, row_num)

                # Check required fields
                for field_name, field_config in fields_config.items():
                    val = row.get(field_name)
                    if field_config.required and (val is None or str(val).strip() == ""):
                        validation_logs.append({
                            "file_name": file_name,
                            "sheet_name": sheet_name,
                            "row_number": row_num,
                            "field_name": field_name,
                            "message": f"Required field '{field_name}' is missing/empty.",
                            "severity": "Error"
                        })
                        invalid_rows_set.add(row_key)

                # Check duplicates based on detected ID column
                if id_field:
                    id_val = row.get(id_field)
                    if id_val is not None and str(id_val).strip() != "":
                        id_str = str(id_val).strip().lower()
                        if id_str in seen_ids:
                            prev_src = seen_ids[id_str]
                            validation_logs.append({
                                "file_name": file_name,
                                "sheet_name": sheet_name,
                                "row_number": row_num,
                                "field_name": id_field,
                                "message": f"Duplicate record detected. Value '{id_val}' in field '{id_field}' already appeared in row {prev_src[2]} of sheet '{prev_src[1]}'.",
                                "severity": "Warning"
                            })
                        else:
                            seen_ids[id_str] = row_key

        # Calculate statistics
        error_count = sum(1 for log in validation_logs if log["severity"] == "Error")
        warning_count = sum(1 for log in validation_logs if log["severity"] == "Warning")
        rows_invalid = len(invalid_rows_set)
        rows_valid = max(0, total_rows_count - rows_invalid)

        statistics = {
            "files_processed": len(merged_files),
            "rows_processed": total_rows_count,
            "rows_valid": rows_valid,
            "rows_invalid": rows_invalid,
            "errors": error_count,
            "warnings": warning_count
        }

        logger.info(f"Validation completed: {statistics}")
        return validation_logs, statistics


validation_service = ValidationService()
