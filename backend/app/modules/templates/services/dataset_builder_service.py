import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DatasetBuilderService:
    def build_standardized_payload(
        self, 
        merged_files: Dict[str, Any], 
        statistics: Dict[str, Any], 
        template_id: str, 
        customer_id: str, 
        dataset_version: int,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """Assembles standard grouped files, statistics, and metadata into a unified JSON object."""
        logger.info(f"Building finalized standardized payload for template '{template_id}' (Version: {dataset_version})...")
        
        # Add execution time to global stats
        stats_payload = dict(statistics)
        stats_payload["processing_time_ms"] = processing_time_ms

        payload = {
            "files": merged_files,
            "global_statistics": stats_payload,
            "metadata": {
                "dataset_version": dataset_version,
                "template_id": str(template_id),
                "customer_id": customer_id
            }
        }
        
        return payload


dataset_builder_service = DatasetBuilderService()
