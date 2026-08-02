import logging
import json
import httpx
from typing import List, Dict, Any
from app.core.exceptions import ValidationException
from app.modules.templates.model import AIConfiguration

logger = logging.getLogger(__name__)

# Check optional library support for OpenAI & Gemini
HAS_OPENAI = False
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    pass

HAS_GEMINI = False
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    pass


class LLMMappingService:
    async def verify_mapping(
        self, 
        required_fields: List[str], 
        uploaded_headers: List[str], 
        ai_config: AIConfiguration
    ) -> Dict[str, str]:
        """Calls the configured LLM provider to map uploaded headers to required template fields.
        
        Returns a dictionary mapping: {required_field_name: uploaded_header_name}
        """
        logger.info(f"Invoking LLM verification mapping via provider: {ai_config.llm_provider} (Model: {ai_config.llm_model})")
        
        prompt = self._build_prompt(required_fields, uploaded_headers)
        
        # 1. Attempt real LLM API calls
        from app.modules.ai.providers.llm_factory import llm_factory
        provider_name = ai_config.llm_provider
        model_name = ai_config.llm_model
        
        try:
            provider = llm_factory.get_provider(provider_name)
            messages = [{"role": "user", "content": prompt}]
            raw_content = await provider.chat(
                messages=messages,
                model=model_name,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            if raw_content and raw_content.strip():
                return self._validate_and_parse_response(raw_content, required_fields, uploaded_headers)
        except Exception as e:
            logger.error(f"Mapping API call failed via LLM provider '{provider_name}': {e}")

        # 2. Mock Fallback Rules Engine
        logger.warning("LLM API keys/connections absent. Using deterministic rules-based mapping engine...")
        return self._mock_similarity_mapping(required_fields, uploaded_headers)

    def _build_prompt(self, required_fields: List[str], uploaded_headers: List[str]) -> str:
        return f"""
You are an expert AI data architect mapping customer spreadsheet columns to template target fields.
Analyze the target required fields and the uploaded Excel headers. Match them based on semantic similarity.

Target Required Fields:
{json.dumps(required_fields, indent=2)}

Uploaded Headers:
{json.dumps(uploaded_headers, indent=2)}

Task:
Return a JSON object mapping each matching Required Field to its corresponding Uploaded Header.
Only match fields where you have moderate-to-high confidence. Do not guess wildly.

Expected Output Format:
{{
  "Patient Name": "Subject",
  "Age": "Years",
  "PT Name": "Preferred Reaction",
  "Listedness": "Expectedness"
}}
Return ONLY valid JSON.
"""

    def _validate_and_parse_response(
        self, 
        raw_response: str, 
        required_fields: List[str], 
        uploaded_headers: List[str]
    ) -> Dict[str, str]:
        """Validates that the LLM response is valid JSON and maps correctly to expected parameters."""
        try:
            mapping = json.loads(raw_response)
        except Exception as e:
            raise ValidationException(f"LLM did not return valid JSON: {e}")

        if not isinstance(mapping, dict):
            raise ValidationException("LLM mapping output must be a JSON dictionary.")

        validated_mapping = {}
        for req_field, uploaded_hdr in mapping.items():
            if req_field in required_fields and uploaded_hdr in uploaded_headers:
                validated_mapping[req_field] = uploaded_hdr
            else:
                logger.warning(f"Ignored invalid LLM mapping: '{req_field}' -> '{uploaded_hdr}'")
        
        return validated_mapping

    def _mock_similarity_mapping(self, required_fields: List[str], uploaded_headers: List[str]) -> Dict[str, str]:
        """A rule-based semantic mapper acting as a fallback local LLM simulator."""
        mapping = {}
        
        # Lowercase mapping rules
        rules = {
            "patient name": ["subject", "patient", "patient full name", "name", "pat name"],
            "age": ["years", "patient age", "age group", "age (yrs)", "age"],
            "pt name": ["preferred reaction", "pt", "pt name", "reaction pt", "preferred term"],
            "listedness": ["expectedness", "listedness", "ccsi listedness", "listed"],
            "reaction description": ["reaction description", "event description", "adverse event", "reaction desc"],
            "narrative": ["case narrative", "description", "narrative", "narrative text", "summary"],
            "suspect drug": ["medicine", "suspect product", "drug", "suspect drug", "suspect drugs"],
            "outcome": ["outcome", "event outcome", "patient outcome"],
            "report id": ["report id", "case id", "icsr id", "id", "report_id"]
        }

        for req in required_fields:
            req_lower = req.strip().lower()
            candidates = rules.get(req_lower, [req_lower])
            
            # Look for exact or alias matches in uploaded headers
            matched = False
            for cand in candidates:
                for header in uploaded_headers:
                    if header.strip().lower() == cand:
                        mapping[req] = header
                        matched = True
                        break
                if matched:
                    break
                    
            # If no rule matches, do basic substring matching
            if not matched:
                for header in uploaded_headers:
                    h_lower = header.strip().lower()
                    if req_lower in h_lower or h_lower in req_lower:
                        mapping[req] = header
                        break
                        
        return mapping


llm_mapping_service = LLMMappingService()
import os
