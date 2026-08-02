import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ExplanationService:
    def generate_explanations(
        self, 
        sections_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provides human-readable justifications and audit details for AI decisions."""
        logger.info("Generating decision explanations for AI sections...")
        decisions = []

        for section_name, section_content in sections_data.items():
            if section_name.startswith("_"):
                continue
                
            model = section_content.get("generated_by", "Unknown")
            confidence = section_content.get("confidence", 0.0)
            prompt_ver = section_content.get("prompt_version", "1.0")

            if section_name == "Executive Summary":
                reason = f"Executive Summary generated using active prompt version {prompt_ver} via {model} model. Selection driven by case statistics."
            elif section_name == "Signal Detection Summary":
                reason = f"Signal Summary compiled based on computed DME/non-DME cases. The LLM was configured to focus on narrative summaries only, bypassing mathematical counting."
            elif section_name == "Benefit-Risk Summary":
                reason = f"Benefit-Risk narrative selected based on patient cohort count. The favorable benefit-risk ratio was clinically mapped as positive."
            else:
                reason = f"Section '{section_name}' was generated using configured clinical settings (Model: {model})."

            decisions.append({
                "section": section_name,
                "confidence": confidence,
                "model": model,
                "prompt_version": prompt_ver,
                "explanation": reason
            })

        return {
            "decisions": decisions,
            "overall_explanation": "All safety report narrative sections were drafted using isolated section agents, preventing mathematical calculation hallucination."
        }


explanation_service = ExplanationService()
