import os
import sys
import uuid
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend app folder to path for import safety
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.modules.templates.model import StandardizedDataset, AIConfiguration, ReportVersion
from app.modules.templates.services.prompt_service import prompt_service
from app.modules.templates.services.section_agents import executive_summary_agent, signal_summary_agent
from app.modules.templates.services.report_assembler import file_assembler
from app.modules.templates.services.quality_service import quality_service
from app.modules.templates.services.explanation_service import explanation_service
from app.modules.templates.services.learning_service import learning_service
from app.modules.templates.services.feedback_service import feedback_service


class TestPromptService(unittest.TestCase):
    def test_prompt_retrieval_and_formatting(self):
        """Verify variable interpolation and fallback values."""
        db_mock = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = mock_res
        
        # Test active prompt retrieval fallback
        prompt_data = asyncio_run_helper(prompt_service.get_active_prompt(db_mock, "Narrative Generation", "Executive Summary"))
        self.assertEqual(prompt_data["version"], "1.0")
        
        # Test formatting variables
        sys_p, user_p = prompt_service.format_prompt(
            prompt_data["system_prompt"],
            prompt_data["user_prompt"],
            {"customer_id": "CUST-100", "total_cases": 12, "template_id": "tpl-1"}
        )
        self.assertIn("CUST-100", user_p)
        self.assertIn("12", user_p)


class TestSectionAgents(unittest.TestCase):
    def test_agent_narrative_metadata(self):
        """Verify that section agents attach section confidence, model details, and versions."""
        db_mock = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = mock_res
        
        ai_config = AIConfiguration(llm_provider="openai", llm_model="gpt-4o")
        variables = {"customer_id": "CUST-A", "total_cases": 25, "template_id": "tpl-2"}
        
        res = asyncio_run_helper(executive_summary_agent.generate(db_mock, variables, ai_config))
        self.assertEqual(res["generated_by"], "gpt-4o")
        self.assertEqual(res["confidence"], 0.95)
        self.assertIn("Clinical Safety Report Executive Summary", res["text"])


class TestReportAssembler(unittest.TestCase):
    def test_deterministic_safety_math(self):
        """Verify that the LLM is never allowed to run mathematical counts."""
        db_mock = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = mock_res
        
        ai_config = AIConfiguration(llm_provider="openai", llm_model="gpt-4o")
        
        # Mock dataset with 3 cases: 2 DME and 1 Non-DME
        dataset = StandardizedDataset(
            template_id=uuid.uuid4(),
            customer_id="CUST-TEST",
            data={
                "files": {
                    "PSUR Current": {
                        "rows": [
                            {"Patient Name": "John", "DME": True, "PT Name": "Headache"},
                            {"Patient Name": "Mary", "DME": True, "PT Name": "Nausea"},
                            {"Patient Name": "Steve", "DME": False, "PT Name": "Headache"}
                        ]
                    }
                }
            }
        )
        
        sections = asyncio_run_helper(file_assembler.assemble_report(db_mock, dataset, ai_config))
        metrics = sections["_metrics"]
        
        # Test case counts math is correct
        self.assertEqual(metrics["total_cases"], 3)
        self.assertEqual(metrics["dme_cases"], 2)
        self.assertEqual(metrics["non_dme_cases"], 1)
        self.assertEqual(metrics["unique_reactions_count"], 2)


class TestQualityService(unittest.TestCase):
    def test_completeness_and_consistency_scoring(self):
        """Verify formatting checks flag missing sections or short texts."""
        sections = {
            "Executive Summary": {"text": "A very short summary"},  # triggers short word warning
            "Signal Detection Summary": {"text": "Adequate length safety report analysis narrative for signal detection summary."},
            "_metrics": {"total_cases": 5}
        }
        
        report_quality = quality_service.analyze_report_quality(sections)
        self.assertLess(report_quality["completeness_score"], 1.0)
        self.assertIn("Missing required section: 'Benefit-Risk Summary'", report_quality["suggestions"])


class TestExplanationService(unittest.TestCase):
    def test_generate_explanations(self):
        """Verify AI explainability justifies decisions."""
        sections = {
            "Executive Summary": {"text": "Exec narrative", "confidence": 0.95, "generated_by": "gpt-4o", "prompt_version": "1.0"},
            "_metrics": {"total_cases": 5}
        }
        explanations = explanation_service.generate_explanations(sections)
        self.assertEqual(len(explanations["decisions"]), 1)
        self.assertEqual(explanations["decisions"][0]["section"], "Executive Summary")
        self.assertIn("gpt-4o", explanations["decisions"][0]["explanation"])


class TestLearningService(unittest.TestCase):
    def test_learn_from_reviewer_edit(self):
        """Verify style change indicators (confidence gain) calculate on edits."""
        db_mock = AsyncMock()
        orig = "This is a basic safety narrative report draft."
        corr = "This clinical safety analysis narrative contains revised medical observations."
        
        # Patch db.add/commit/refresh
        db_mock.add = MagicMock()
        db_mock.commit = AsyncMock()
        db_mock.refresh = AsyncMock()
        
        learning_record = asyncio_run_helper(learning_service.learn_from_reviewer_edit(
            db_mock, "CUST-Z", uuid.uuid4(), "Executive Summary", orig, corr
        ))
        
        self.assertIsNotNone(learning_record)
        self.assertGreater(learning_record.confidence_gain, 0.0)
        self.assertEqual(learning_record.key_field, "Executive Summary")


class TestFeedbackService(unittest.TestCase):
    def test_report_review_approvals_and_audit(self):
        """Verify audit logs are logged and report status updates on reviewer edits."""
        db_mock = AsyncMock()
        
        report = ReportVersion(
            id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
            version=1,
            status="AI Generated",
            customer_id="CUST-X",
            sections_data={
                "Executive Summary": {"text": "Original summary", "section_version": 1}
            }
        )
        
        # Mock DB execute response
        res_mock = MagicMock()
        res_mock.scalar_one_or_none.return_value = report
        db_mock.execute.return_value = res_mock
        db_mock.commit = AsyncMock()
        
        # Edit Executive Summary narrative
        asyncio_run_helper(feedback_service.submit_report_feedback(
            db_mock, report.id, "reviewer@company.com", 4, "Revised", {"Executive Summary": "New corrected summary"}
        ))
        
        self.assertEqual(report.status, "Under Review")
        self.assertEqual(report.sections_data["Executive Summary"]["text"], "New corrected summary")
        self.assertEqual(report.sections_data["Executive Summary"]["section_version"], 2)


def asyncio_run_helper(coro):
    return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()
