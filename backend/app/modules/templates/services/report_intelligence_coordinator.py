import logging
import uuid
import time
from typing import Dict, Any, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.templates.model import (
    StandardizedDataset, 
    ReportVersion, 
    ReportGeneration, 
    AIProcessingLog, 
    AIConfiguration
)
from app.modules.templates.services.template_service import template_service
from app.modules.templates.services.report_assembler import file_assembler
from app.modules.templates.services.quality_service import quality_service
from app.modules.templates.services.explanation_service import explanation_service

logger = logging.getLogger(__name__)


class ReportIntelligenceCoordinator:
    async def generate_assisted_report(
        self,
        db: AsyncSession,
        dataset_id: uuid.UUID,
        generated_by: str
    ) -> ReportVersion:
        """Assembles clinical narrative sections, scores output quality, and logs telemetry details."""
        start_time = time.time()
        logger.info(f"[Report Coordinator] Generating report for dataset {dataset_id} (Author: {generated_by})")

        # 1. Fetch StandardizedDataset
        stmt_ds = select(StandardizedDataset).where(StandardizedDataset.id == dataset_id)
        res_ds = await db.execute(stmt_ds)
        dataset = res_ds.scalar_one_or_none()
        if not dataset:
            raise NotFoundException("Standardized dataset not found")
        if dataset.processing_status != "Completed":
            raise ValidationException("Dataset is not fully processed or standardized. Complete Phase 3 first.")

        # 2. Fetch AI configurations
        ai_config = await template_service.get_ai_config(db)

        # 3. Resolve next report version sequence
        stmt_ver = select(func.max(ReportVersion.version)).where(
            and_(
                ReportVersion.template_id == dataset.template_id,
                ReportVersion.dataset_id == dataset_id
            )
        )
        res_ver = await db.execute(stmt_ver)
        max_ver = res_ver.scalar() or 0
        new_version = max_ver + 1

        # 4. Generate safety sections narratives via assembler
        sections_data = await file_assembler.assemble_report(db, dataset, ai_config)
        duration_ms = int((time.time() - start_time) * 1000)

        # 5. Run Quality analyzer
        quality_info = quality_service.analyze_report_quality(sections_data)
        
        # 6. Run Explainability builder
        explanation_info = explanation_service.generate_explanations(sections_data)

        # 7. Create and save ReportVersion
        report_version = ReportVersion(
            template_id=dataset.template_id,
            dataset_id=dataset.id,
            version=new_version,
            status="AI Generated",
            generated_by=generated_by,
            sections_data=sections_data
        )
        db.add(report_version)
        await db.commit()
        await db.refresh(report_version)

        # 8. Create ReportGeneration metrics record
        generation_log = ReportGeneration(
            report_version_id=report_version.id,
            quality_score=quality_info["overall_score"],
            quality_suggestions=quality_info,
            explanations=explanation_info
        )
        db.add(generation_log)

        # 9. Create AIProcessingLog telemetry logs
        processing_log = AIProcessingLog(
            processing_step="Report Narrative Generation",
            provider=ai_config.llm_provider,
            model=ai_config.llm_model,
            tokens_used=1250,  # Simulated usage
            duration_ms=duration_ms,
            status="Success",
            prompt_version="1.0",
            dataset_version=dataset.dataset_version
        )
        db.add(processing_log)
        await db.commit()

        logger.info(f"[Report Coordinator] Report version {new_version} created successfully. Quality score: {quality_info['overall_score']}")
        return report_version

    async def get_report(self, db: AsyncSession, report_id: uuid.UUID) -> ReportVersion:
        """Retrieves a report version details by ID."""
        stmt = select(ReportVersion).where(ReportVersion.id == report_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()
        if not report:
            raise NotFoundException("Report version not found")
        return report

    async def get_report_generation(self, db: AsyncSession, report_id: uuid.UUID) -> ReportGeneration:
        """Retrieves report generation metrics (quality, explanations) by report version ID."""
        stmt = select(ReportGeneration).where(ReportGeneration.report_version_id == report_id)
        res = await db.execute(stmt)
        gen = res.scalar_one_or_none()
        if not gen:
            raise NotFoundException("Report generation metrics not found for this version")
        return gen


report_intelligence_coordinator = ReportIntelligenceCoordinator()
