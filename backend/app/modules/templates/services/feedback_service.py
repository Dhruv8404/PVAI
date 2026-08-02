import logging
import uuid
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.modules.templates.model import ReportVersion, ReportAudit
from app.modules.templates.services.learning_service import learning_service

logger = logging.getLogger(__name__)


class FeedbackService:
    async def submit_report_feedback(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        performed_by: str,
        rating: int,
        comments: str,
        narrative_corrections: Dict[str, str]  # {section_name: corrected_text}
    ) -> None:
        """Applies manual reviewer narrative edits, logs change audits, and triggers learning engine."""
        logger.info(f"Submitting feedback for report version {report_id} by {performed_by}")

        # 1. Fetch ReportVersion record
        stmt = select(ReportVersion).where(ReportVersion.id == report_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()
        if not report:
            raise NotFoundException("Report version not found")

        # 2. Iterate and apply section corrections
        sections_data = dict(report.sections_data)
        
        for section, corrected_text in narrative_corrections.items():
            if section in sections_data:
                orig_text = sections_data[section].get("text", "")
                
                if orig_text.strip() != corrected_text.strip():
                    logger.info(f"Applying correction for section '{section}'")
                    
                    # Log audit trail
                    audit = ReportAudit(
                        report_id=report.id,
                        section_name=section,
                        action="Edited",
                        performed_by=performed_by,
                        old_value=orig_text,
                        new_value=corrected_text
                    )
                    db.add(audit)
                    
                    # Update report narrative text
                    sections_data[section]["text"] = corrected_text
                    # Increment section-level version
                    sections_data[section]["section_version"] = sections_data[section].get("section_version", 1) + 1
                    
                    # Trigger learning service to learn preference styles
                    await learning_service.learn_from_reviewer_edit(
                        db=db,
                        customer_id=report.customer_id,
                        template_id=report.template_id,
                        section_name=section,
                        original_text=orig_text,
                        corrected_text=corrected_text
                    )

        # 3. Save sections updates and update status
        report.sections_data = sections_data
        report.status = "Under Review"
        await db.commit()

    async def approve_report(
        self,
        db: AsyncSession,
        report_id: uuid.UUID,
        performed_by: str
    ) -> None:
        """Promotes report version status to Approved and logs audit trail."""
        logger.info(f"Approving report version {report_id} by {performed_by}")
        
        stmt = select(ReportVersion).where(ReportVersion.id == report_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()
        if not report:
            raise NotFoundException("Report version not found")
            
        old_status = report.status
        report.status = "Approved"
        
        audit = ReportAudit(
            report_id=report.id,
            section_name="Report Status",
            action="Approved",
            performed_by=performed_by,
            old_value=old_status,
            new_value="Approved"
        )
        db.add(audit)
        await db.commit()

    async def get_audit_trail(
        self,
        db: AsyncSession,
        report_id: uuid.UUID
    ) -> List[ReportAudit]:
        """Retrieves history of audits associated with a report version."""
        stmt = select(ReportAudit).where(ReportAudit.report_id == report_id).order_by(ReportAudit.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())


feedback_service = FeedbackService()
