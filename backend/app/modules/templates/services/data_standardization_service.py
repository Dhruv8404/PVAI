import logging
import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.modules.templates.model import TemplateField

logger = logging.getLogger(__name__)


def parse_iso_date(val: Any) -> Optional[str]:
    """Robust date parsing helper supporting Excel serial numbers, datetimes, and strings."""
    if val is None:
        return None
        
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.strftime("%Y-%m-%d")
        
    # Excel float serial date number
    if isinstance(val, (int, float)):
        try:
            # Excel leap year bug base is 1899-12-30
            base = datetime.date(1899, 12, 30)
            delta = datetime.timedelta(days=float(val))
            return (base + delta).strftime("%Y-%m-%d")
        except Exception:
            pass

    if isinstance(val, str) and val.strip():
        val_str = val.strip()
        
        # Strip potential time suffix e.g. '00:00:00'
        if " " in val_str:
            val_str = val_str.split()[0]
            
        # Try common date string formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
                
    return None


class DataStandardizationService:
    def standardize_row(
        self, 
        raw_row: Dict[str, Any], 
        fields_config: Dict[str, TemplateField]  # {field_name: TemplateField}
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Normalizes and standardizes cell values in a single row based on field types.
        
        Returns a tuple: (standardized_row, validation_issues)
        """
        standardized = {}
        issues = []
        
        # Keep source provenance unchanged
        if "_source" in raw_row:
            standardized["_source"] = raw_row["_source"]

        for field_name, field_config in fields_config.items():
            raw_val = raw_row.get(field_name)
            
            # Skip if value is missing and not required (let validator check required status)
            if raw_val is None or str(raw_val).strip() == "":
                standardized[field_name] = None
                continue

            data_type = field_config.data_type.lower()
            try:
                if data_type == "string":
                    standardized[field_name] = str(raw_val).strip()
                    
                elif data_type == "integer":
                    try:
                        # strip decimals if read as float e.g. 45.0 -> 45
                        val_str = str(raw_val).split(".")[0].strip()
                        standardized[field_name] = int(val_str)
                    except ValueError:
                        standardized[field_name] = None
                        issues.append({
                            "field_name": field_name,
                            "message": f"Value '{raw_val}' is not a valid integer.",
                            "severity": "Error"
                        })
                        
                elif data_type == "float":
                    try:
                        standardized[field_name] = float(str(raw_val).strip())
                    except ValueError:
                        standardized[field_name] = None
                        issues.append({
                            "field_name": field_name,
                            "message": f"Value '{raw_val}' is not a valid decimal float number.",
                            "severity": "Error"
                        })
                        
                elif data_type == "boolean":
                    val_str = str(raw_val).strip().lower()
                    if val_str in ("true", "1", "yes", "y", "t"):
                        standardized[field_name] = True
                    elif val_str in ("false", "0", "no", "n", "f"):
                        standardized[field_name] = False
                    else:
                        standardized[field_name] = None
                        issues.append({
                            "field_name": field_name,
                            "message": f"Value '{raw_val}' is not a valid boolean indicator.",
                            "severity": "Warning"
                        })
                        
                elif data_type == "date":
                    date_parsed = parse_iso_date(raw_val)
                    if date_parsed:
                        standardized[field_name] = date_parsed
                    else:
                        standardized[field_name] = None
                        issues.append({
                            "field_name": field_name,
                            "message": f"Value '{raw_val}' could not be parsed into YYYY-MM-DD date format.",
                            "severity": "Error"
                        })
                        
                elif data_type == "enum":
                    val_str = str(raw_val).strip()
                    # Check examples/aliases for enum case matching
                    examples = field_config.examples or []
                    matched = False
                    for ex in examples:
                        if ex.strip().lower() == val_str.lower():
                            standardized[field_name] = ex.strip()
                            matched = True
                            break
                    if not matched:
                        # Fallback: keep original trimmed string, but log a warning
                        standardized[field_name] = val_str
                        issues.append({
                            "field_name": field_name,
                            "message": f"Value '{raw_val}' matches no predefined enum categories: {examples}.",
                            "severity": "Warning"
                        })
                        
            except Exception as e:
                standardized[field_name] = None
                issues.append({
                    "field_name": field_name,
                    "message": f"Unexpected formatting error: {str(e)}",
                    "severity": "Error"
                })

        return standardized, issues


data_standardization_service = DataStandardizationService()
from typing import Tuple
