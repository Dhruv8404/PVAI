import logging
import uuid
import time
from datetime import datetime, UTC
from typing import List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.core.exceptions import ValidationException, NotFoundException
from app.modules.templates.model import HtmlTemplate, StandardizedDataset, ValidationLog, CustomerHeaderMapping, TemplateField, ExcelUploadSession
from app.modules.templates.services.template_service import template_service
from app.modules.templates.services.excel_data_service import excel_data_service
from app.modules.templates.services.data_standardization_service import data_standardization_service
from app.modules.templates.services.file_merge_service import file_merge_service
from app.modules.templates.services.validation_service import validation_service
from app.modules.templates.services.dataset_builder_service import dataset_builder_service
from app.modules.templates.services.header_mapping_coordinator import header_mapping_coordinator

logger = logging.getLogger(__name__)


class DataStandardizationCoordinator:
    async def standardize_customer_data(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        customer_id: str,
        files: List[UploadFile]
    ) -> StandardizedDataset:
        """Runs the entire Phase 3 data standardization and validation pipeline in transaction context.
        
        Returns the finalized StandardizedDataset database record.
        """
        start_time = time.time()
        logger.info(f"[Standardization Pipeline] Starting run for customer {customer_id} on template {template_id}")

        # 1. Verify template exists
        template = await template_service.get_template(db, template_id)
        required_files_list = template.required_files or []

        # 2. Get customer mappings cache
        stmt_map = select(CustomerHeaderMapping).where(
            and_(
                CustomerHeaderMapping.template_id == template_id,
                CustomerHeaderMapping.customer_id == customer_id
            )
        )
        res_map = await db.execute(stmt_map)
        mappings = res_map.scalars().all()
        
        # Build mappings map: {uploaded_header_lowercase: mapped_field_name}
        mappings_dict = {m.uploaded_header.strip().lower(): m.mapped_field for m in mappings}
        
        # 3. If mapping cache is empty, attempt fuzzy auto-mapping discovery
        if not mappings_dict:
            logger.info("[Standardization Pipeline] Mappings cache empty. Auto-discovering headers...")
            # Automatically parse headers and run similarity logic
            await header_mapping_coordinator.analyze_uploaded_headers(db, template_id, customer_id, files)
            # Re-fetch mappings
            res_map = await db.execute(stmt_map)
            mappings = res_map.scalars().all()
            mappings_dict = {m.uploaded_header.strip().lower(): m.mapped_field for m in mappings}
            if not mappings_dict:
                raise ValidationException("No column mappings found or auto-discovered. Complete Phase 2 first.")

        # 4. Resolve template fields configurations
        stmt_fields = select(TemplateField).where(TemplateField.template_id == template_id)
        res_fields = await db.execute(stmt_fields)
        fields_list = res_fields.scalars().all()
        fields_config = {f.field_name: f for f in fields_list}

        # 5. Resolve new dataset version sequence
        stmt_ver = select(func.max(StandardizedDataset.dataset_version)).where(
            and_(
                StandardizedDataset.template_id == template_id,
                StandardizedDataset.customer_id == customer_id
            )
        )
        res_ver = await db.execute(stmt_ver)
        max_ver = res_ver.scalar() or 0
        new_version = max_ver + 1

        # 6. Initialize StandardizedDataset record as "Reading"
        dataset_obj = StandardizedDataset(
            template_id=template_id,
            customer_id=customer_id,
            dataset_version=new_version,
            processing_status="Reading",
            data={},
            statistics={}
        )
        db.add(dataset_obj)
        await db.commit()
        await db.refresh(dataset_obj)

        try:
            # --- STAGE 1: Reading Files ---
            raw_datasets_list = []
            for file in files:
                file_name = file.filename or "unknown.xlsx"
                file_content = await file.read()
                await file.seek(0)
                
                # Match to expected file type (e.g. PSUR Current)
                expected_type = await header_mapping_coordinator.match_file_to_expected_type(file_name, required_files_list)
                
                # Extract rows
                extracted_rows = excel_data_service.extract_rows(file_content, file_name, expected_type, mappings_dict)
                raw_datasets_list.append((expected_type, extracted_rows))

            # --- STAGE 2: Standardizing Data ---
            dataset_obj.processing_status = "Standardizing"
            await db.commit()

            normalized_datasets_list = []
            all_standardization_issues = []

            for expected_type, raw_rows in raw_datasets_list:
                normalized_rows = []
                for raw_row in raw_rows:
                    standardized_row, issues = data_standardization_service.standardize_row(raw_row, fields_config)
                    normalized_rows.append(standardized_row)
                    
                    # Attach source provenance to issues
                    for issue in issues:
                        issue["_source"] = raw_row.get("_source")
                        all_standardization_issues.append(issue)
                        
                normalized_datasets_list.append((expected_type, normalized_rows))

            # --- STAGE 3: Merging ---
            dataset_obj.processing_status = "Merging"
            await db.commit()

            merged_files = file_merge_service.merge_datasets(normalized_datasets_list)

            # --- STAGE 4: Validating ---
            dataset_obj.processing_status = "Validating"
            await db.commit()

            validation_logs, statistics = validation_service.validate_dataset(
                merged_files=merged_files,
                fields_config=fields_config,
                standardization_issues=all_standardization_issues
            )

            # --- STAGE 5: Building Dataset ---
            dataset_obj.processing_status = "Building"
            await db.commit()

            processing_time_ms = int((time.time() - start_time) * 1000)
            
            final_payload = dataset_builder_service.build_standardized_payload(
                merged_files=merged_files,
                statistics=statistics,
                template_id=template_id,
                customer_id=customer_id,
                dataset_version=new_version,
                processing_time_ms=processing_time_ms
            )

            # 7. Write results to DB and set status to Completed
            dataset_obj.data = final_payload
            dataset_obj.statistics = statistics
            dataset_obj.processing_status = "Completed"
            await db.commit()

            # 8. Write validation logs to DB
            for log in validation_logs:
                new_log = ValidationLog(
                    dataset_id=dataset_obj.id,
                    file_name=log.get("file_name"),
                    sheet_name=log.get("sheet_name"),
                    row_number=log.get("row_number"),
                    field_name=log.get("field_name"),
                    message=log.get("message"),
                    severity=log.get("severity")
                )
                db.add(new_log)
            
            await db.commit()
            logger.info(f"[Standardization Pipeline] Completed run successfully in {processing_time_ms} ms. Dataset ID: {dataset_obj.id}")
            return dataset_obj

        except Exception as e:
            logger.error(f"[Standardization Pipeline] Critical failure: {e}")
            dataset_obj.processing_status = "Failed"
            await db.commit()
            raise e

    async def get_validation_logs(
        self,
        db: AsyncSession,
        template_id: uuid.UUID
    ) -> List[ValidationLog]:
        """Retrieves validation logs for the last processed dataset under a template."""
        # Find latest completed dataset
        stmt_ds = select(StandardizedDataset).where(
            and_(
                StandardizedDataset.template_id == template_id,
                StandardizedDataset.processing_status == "Completed"
            )
        ).order_by(StandardizedDataset.created_at.desc())
        res_ds = await db.execute(stmt_ds)
        latest_dataset = res_ds.scalars().first()
        
        if not latest_dataset:
            return []
            
        stmt_log = select(ValidationLog).where(ValidationLog.dataset_id == latest_dataset.id).order_by(ValidationLog.created_at.asc())
        res_log = await db.execute(stmt_log)
        return list(res_log.scalars().all())

    async def get_dataset(self, db: AsyncSession, dataset_id: uuid.UUID) -> StandardizedDataset:
        """Retrieves a standardized dataset by ID."""
        stmt = select(StandardizedDataset).where(StandardizedDataset.id == dataset_id)
        res = await db.execute(stmt)
        dataset = res.scalar_one_or_none()
        if not dataset:
            raise NotFoundException("Standardized dataset not found")
        return dataset


data_standardization_coordinator = DataStandardizationCoordinator()
