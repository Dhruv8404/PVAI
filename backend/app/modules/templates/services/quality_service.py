import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class QualityService:
    def analyze_report_quality(
        self, 
        sections_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Performs safety checks on the report structure to verify clinical documentation standards."""
        logger.info("Analyzing report narratives quality and formatting...")
        
        suggestions = []
        scores = {
            "completeness": 1.0,
            "consistency": 1.0,
            "formatting": 1.0
        }

        # 1. Completeness check
        required_sections = ["Executive Summary", "Signal Detection Summary", "Benefit-Risk Summary", "Recommendations"]
        missing_count = 0
        for req in required_sections:
            if req not in sections_data or not sections_data[req].get("text"):
                missing_count += 1
                suggestions.append(f"Missing required section: '{req}'")
            else:
                text_len = len(sections_data[req]["text"].split())
                if text_len < 15:
                    suggestions.append(f"Section '{req}' is too short ({text_len} words). Expand detail.")
                    scores["completeness"] = max(0.4, scores["completeness"] - 0.15)

        if missing_count > 0:
            scores["completeness"] = max(0.0, 1.0 - (missing_count * 0.25))

        # 2. Consistency check (Compare narrative numbers to metrics calculations)
        metrics = sections_data.get("_metrics", {})
        total_cases = metrics.get("total_cases", 0)
        
        for name, content in sections_data.items():
            if name.startswith("_"):
                continue
            text = content.get("text", "")
            
            # Simple consistency scan: if text contains cases numbers, they should align
            if "cases" in text.lower():
                # Verify if total case counts mismatch
                for word in text.split():
                    clean_word = "".join(c for c in word if c.isdigit())
                    if clean_word and int(clean_word) > 0:
                        val = int(clean_word)
                        # If a large number is mentioned and it differs from cases count, log suggestion
                        if val > 10 and val != total_cases and total_cases > 0 and abs(val - total_cases) < 10:
                            suggestions.append(f"Numeric mismatch suspect in '{name}': narrative mentions '{val}' cases, while database has '{total_cases}' cases.")
                            scores["consistency"] = max(0.5, scores["consistency"] - 0.1)

        # 3. Formatting check (verify if recommendations are bulleted or clear)
        recs_text = sections_data.get("Recommendations", {}).get("text", "")
        if recs_text and "\n" not in recs_text and "-" not in recs_text:
            suggestions.append("Format Recommendations as bullet points for improved actionability.")
            scores["formatting"] = 0.85

        # Calculate overall score
        overall_score = round(sum(scores.values()) / len(scores), 2)
        
        return {
            "overall_score": overall_score,
            "completeness_score": round(scores["completeness"], 2),
            "consistency_score": round(scores["consistency"], 2),
            "formatting_score": round(scores["formatting"], 2),
            "suggestions": suggestions
        }


quality_service = QualityService()
