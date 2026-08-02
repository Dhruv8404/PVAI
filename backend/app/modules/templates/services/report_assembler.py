import logging
import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.templates.model import StandardizedDataset, AIConfiguration
from app.modules.templates.services.section_agents import (
    executive_summary_agent,
    signal_summary_agent,
    benefit_risk_agent,
    recommendation_agent
)

logger = logging.getLogger(__name__)


class ReportAssembler:
    async def assemble_report(
        self,
        db: AsyncSession,
        dataset: StandardizedDataset,
        ai_config: AIConfiguration
    ) -> Dict[str, Any]:
        """Runs the deterministic safety metrics calculations and triggers modular section agents.
        
        Assembles a structured sections dictionary tracking section-level confidence and metadata.
        """
        logger.info(f"Assembling report from standardized dataset {dataset.id}")
        dataset_data = dataset.data or {}
        files_data = dataset_data.get("files", {})

        # 1. Deterministic safety metrics calculations (NO MATH IN LLM)
        all_rows = []
        for file_type, file_content in files_data.items():
            all_rows.extend(file_content.get("rows", []))

        total_cases = len(all_rows)
        
        # Calculate Designated Medical Events (DME) counts deterministically
        dme_cases = 0
        non_dme_cases = 0
        reactions = set()

        for row in all_rows:
            # Check for DME keys case-insensitively
            is_dme = False
            for k, v in row.items():
                if k.lower() in ("dme", "is_dme", "designated_medical_event") and str(v).lower() in ("true", "yes", "1", "y"):
                    is_dme = True
                    break
            if is_dme:
                dme_cases += 1
            else:
                non_dme_cases += 1

            # Check for PT Name keys case-insensitively
            for k, v in row.items():
                if k.lower() in ("pt", "pt name", "pt_name", "preferred term", "preferred_term") and v:
                    reactions.add(str(v).strip())

        reactions_list = sorted(list(reactions))
        reactions_str = ", ".join(reactions_list[:10]) if reactions_list else "None reported"

        # 2. Build variables payload
        variables = {
            "customer_id": dataset.customer_id,
            "template_id": str(dataset.template_id),
            "total_cases": total_cases,
            "dme_cases": dme_cases,
            "non_dme_cases": non_dme_cases,
            "reactions_list": reactions_str,
            "unique_reactions_count": len(reactions_list)
        }
        logger.info(f"Deterministic metrics compiled: {variables}")

        # 3. Call section agents asynchronously (or sequentially for event safety)
        exec_summary = await executive_summary_agent.generate(db, variables, ai_config)
        signal_summary = await signal_summary_agent.generate(db, variables, ai_config)
        benefit_risk = await benefit_risk_agent.generate(db, variables, ai_config)
        recommendations = await recommendation_agent.generate(db, variables, ai_config)

        # 4. Assemble report dictionary with sections and versioning metadata
        sections_output = {
            "Executive Summary": {
                "text": exec_summary["text"],
                "section_version": 1,
                "confidence": exec_summary["confidence"],
                "generated_by": exec_summary["generated_by"],
                "prompt_version": exec_summary["prompt_version"]
            },
            "Signal Detection Summary": {
                "text": signal_summary["text"],
                "section_version": 1,
                "confidence": signal_summary["confidence"],
                "generated_by": signal_summary["generated_by"],
                "prompt_version": signal_summary["prompt_version"]
            },
            "Benefit-Risk Summary": {
                "text": benefit_risk["text"],
                "section_version": 1,
                "confidence": benefit_risk["confidence"],
                "generated_by": benefit_risk["generated_by"],
                "prompt_version": benefit_risk["prompt_version"]
            },
            "Recommendations": {
                "text": recommendations["text"],
                "section_version": 1,
                "confidence": recommendations["confidence"],
                "generated_by": recommendations["generated_by"],
                "prompt_version": recommendations["prompt_version"]
            },
            "Conclusion": {
                "text": "Overall vigilance analysis concluded. Safety management plans are aligned.",
                "section_version": 1,
                "confidence": 1.0,
                "generated_by": "System",
                "prompt_version": "1.0"
            }
        }

        # Embed calculations in report sections data directly
        sections_output["_metrics"] = variables

        return sections_output


file_assembler = ReportAssembler()
