import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class FileMergeService:
    def merge_datasets(
        self, 
        datasets_list: List[Tuple[str, List[Dict[str, Any]]]]  # List of tuples: (expected_file_type, rows_list)
    ) -> Dict[str, Any]:
        """Merges multiple spreadsheets' extracted rows under their respective expected file type labels.
        
        Output format:
        {
            "PSUR Current": {
                "rows": [ ... ]
            },
            "ES Current": {
                "rows": [ ... ]
            }
        }
        """
        logger.info(f"Merging {len(datasets_list)} file datasets...")
        merged_files = {}
        
        for expected_type, rows in datasets_list:
            if not expected_type or expected_type == "Unknown":
                continue
                
            if expected_type not in merged_files:
                merged_files[expected_type] = {
                    "rows": []
                }
                
            merged_files[expected_type]["rows"].extend(rows)
            logger.info(f"Merged {len(rows)} rows into file category '{expected_type}'")

        return merged_files


file_merge_service = FileMergeService()
