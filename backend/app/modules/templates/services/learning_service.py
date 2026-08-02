import logging
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.templates.model import LearningHistory

logger = logging.getLogger(__name__)


class LearningService:
    async def learn_from_reviewer_edit(
        self,
        db: AsyncSession,
        customer_id: str,
        template_id: uuid.UUID,
        section_name: str,
        original_text: str,
        corrected_text: str
    ) -> LearningHistory:
        """Analyzes corrections made by safety reviewers and registers stylistic metrics.
        
        Saves writing style alignment logs in the LearningHistory database table.
        """
        logger.info(f"Learning engine triggered for section '{section_name}' (Customer: {customer_id})")
        
        orig_clean = (original_text or "").strip()
        corr_clean = (corrected_text or "").strip()
        
        if orig_clean == corr_clean:
            logger.info("No modifications detected in section. Skipping learning updates.")
            # Return a dummy or empty model
            return None

        # 1. Compute stylistic metrics: length variance, word count differences
        orig_words = orig_clean.split()
        corr_words = corr_clean.split()
        word_diff = len(corr_words) - len(orig_words)
        
        # Calculate style change indicator (confidence gain)
        # Larger edits indicate lower initial alignment, resulting in a higher confidence gain value upon learning
        similarity_ratio = len(set(orig_words) & set(corr_words)) / max(1, len(set(orig_words) | set(corr_words)))
        confidence_gain = round(1.0 - similarity_ratio, 4)
        
        logger.info(f"[Learning Engine] Style similarity: {similarity_ratio:.2f}. Confidence gain logged: {confidence_gain}")

        # 2. Save historical record
        learning_record = LearningHistory(
            source_action="Reviewer Narrative Edit",
            customer_id=customer_id,
            template_id=template_id,
            key_field=section_name,
            original_value=orig_clean,
            corrected_value=corr_clean,
            confidence_gain=confidence_gain
        )
        db.add(learning_record)
        await db.commit()
        await db.refresh(learning_record)
        
        return learning_record


learning_service = LearningService()
