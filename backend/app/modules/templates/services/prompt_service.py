import logging
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.templates.model import PromptTemplate

logger = logging.getLogger(__name__)

# Default fallback prompt templates for the report narrative sections
DEFAULT_PROMPTS = {
    "Executive Summary": {
        "system_prompt": "You are a clinical pharmacovigilance specialist compiling an Executive Summary for safety reporting. Maintain a professional, objective tone.",
        "user_prompt": "Review the safety statistics for {customer_id}.\nTotal Cases Analysed: {total_cases}.\nTarget Template: {template_id}.\nProvide a brief clinical summary of the findings.",
        "version": "1.0"
    },
    "Signal Detection Summary": {
        "system_prompt": "You are a senior safety scientist writing a Signal Detection Summary section. Do not perform any mathematical math calculations.",
        "user_prompt": "Summarize safety signals based on raw data counts.\nDME cases: {dme_cases}.\nNon-DME cases: {non_dme_cases}.\nTotal cases: {total_cases}.\nDocument clinical safety observations.",
        "version": "1.0"
    },
    "Benefit-Risk Summary": {
        "system_prompt": "You are a medical reviewer writing a Benefit-Risk Summary section.",
        "user_prompt": "Provide a benefit-risk assessment summary for customer {customer_id}.\nTotal cases reported: {total_cases}.\nDME counts: {dme_cases}.",
        "version": "1.0"
    },
    "Recommendations": {
        "system_prompt": "You are a safety officer writing Recommendations for a clinical report.",
        "user_prompt": "List safety recommendations based on the findings.\nTotal cases analyzed: {total_cases}.\nIdentify if any risk mitigation strategies are recommended.",
        "version": "1.0"
    }
}


class PromptService:
    async def get_active_prompt(
        self,
        db: AsyncSession,
        template_type: str,
        prompt_name: str
    ) -> Dict[str, Any]:
        """Fetches the active versioned PromptTemplate from the database.
        
        Falls back to default built-in templates if none exist in the database.
        """
        logger.info(f"Retrieving active prompt template: '{prompt_name}' (Category: {template_type})")
        
        try:
            stmt = select(PromptTemplate).where(
                and_(
                    PromptTemplate.template_type == template_type,
                    PromptTemplate.prompt_name == prompt_name,
                    PromptTemplate.is_active == True
                )
            )
            res = await db.execute(stmt)
            prompt_obj = res.scalar_one_or_none()
            
            if prompt_obj:
                return {
                    "system_prompt": prompt_obj.system_prompt,
                    "user_prompt": prompt_obj.user_prompt,
                    "version": prompt_obj.prompt_version,
                    "from_db": True
                }
        except Exception as e:
            logger.error(f"Failed to fetch prompt from database: {e}")
            
        # Fallback to defaults
        fallback = DEFAULT_PROMPTS.get(prompt_name)
        if fallback:
            logger.info(f"[Prompt Fallback] Using default fallback prompt for '{prompt_name}'")
            return {
                "system_prompt": fallback["system_prompt"],
                "user_prompt": fallback["user_prompt"],
                "version": fallback["version"],
                "from_db": False
            }
            
        # Return generic prompt if no mapping matches
        return {
            "system_prompt": "You are a pharmacovigilance assistant.",
            "user_prompt": "Summarize the dataset details: {variables}.",
            "version": "0.1-generic",
            "from_db": False
        }

    def format_prompt(self, system_prompt: str, user_prompt: str, variables: Dict[str, Any]) -> Tuple[str, str]:
        """Interpolates variables inside prompt strings using python format block matching."""
        try:
            formatted_sys = system_prompt.format(**variables)
        except Exception as e:
            logger.warning(f"Failed formatting system prompt: {e}")
            formatted_sys = system_prompt

        try:
            formatted_user = user_prompt.format(**variables)
        except Exception as e:
            logger.warning(f"Failed formatting user prompt: {e}")
            # Fallback formatting: join values
            flat_vars = ", ".join(f"{k}={v}" for k, v in variables.items())
            formatted_user = f"{user_prompt}\n\nVariables context: {flat_vars}"
            
        return formatted_sys, formatted_user


prompt_service = PromptService()
from typing import Tuple
