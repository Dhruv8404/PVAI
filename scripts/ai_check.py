import os
import sys
import asyncio
import logging

# Configure basic logging for script output
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("ai_check")

# Add backend directory to python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

try:
    from app.core.config import settings
    from app.modules.ai.embeddings.embedding_service import embedding_service
    from app.modules.ai.vector_db.chroma_service import chroma_service
    from app.modules.ai.providers.llm_factory import llm_factory
except ImportError as e:
    logger.error(f"Failed to import backend AI modules: {e}")
    logger.error("Make sure to run this script inside virtual environment.")
    sys.exit(1)


async def check_embeddings() -> bool:
    logger.info(f"Checking embedding model preloading: {settings.EMBEDDING_MODEL}...")
    try:
        embedding_service.load_model()
        if embedding_service.is_loaded():
            logger.info("✓ Embedding Model Load: PASS")
            # Verify actual generation works
            vector = embedding_service.generate_embedding("smoke test")
            if len(vector) == 384:
                logger.info("✓ Embedding Generation (384 dims): PASS")
                return True
            else:
                logger.error(f"✗ Embedding Vector size mismatched: {len(vector)} dims")
                return False
        else:
            logger.warning("⚠ Embedding Model Load: DEGRADED (Using mock fallback embeddings)")
            return True
    except Exception as e:
        logger.warning(f"⚠ Embedding Model Load: DEGRADED (Service Exception: {e}. Using mock fallback embeddings)")
        return True


async def check_chromadb() -> bool:
    logger.info("Checking ChromaDB Vector DB connection...")
    try:
        chroma_service.initialize()
        if chroma_service.is_connected():
            logger.info("✓ ChromaDB Connection: PASS")
            
            # Smoke test get/create collection
            col = chroma_service.get_or_create_collection("smoke_test_collection")
            if col is not None:
                logger.info("✓ ChromaDB Collection Access: PASS")
                chroma_service.delete_collection("smoke_test_collection")
                return True
            else:
                logger.error("✗ ChromaDB Collection Access: FAIL")
                return False
        else:
            logger.warning("⚠ ChromaDB Connection: DEGRADED (Using in-memory mock fallback vector store)")
            return True
    except Exception as e:
        logger.warning(f"⚠ ChromaDB Connection: DEGRADED (Service Exception: {e}. Using in-memory mock fallback vector store)")
        return True


async def check_llm_provider() -> bool:
    provider_name = settings.LLM_PROVIDER
    logger.info(f"Checking LLM Provider connectivity: {provider_name}...")
    try:
        provider = llm_factory.get_provider()
        is_valid = await provider.validate()
        if is_valid:
            logger.info(f"✓ LLM Provider '{provider_name}' Connection: PASS")
            return True
        else:
            logger.warning(f"⚠ LLM Provider '{provider_name}' Connection: FAIL (API Key invalid or endpoint unreachable)")
            return True # Allowed to pass as it's optional on startup
    except Exception as e:
        logger.error(f"✗ LLM Provider check exception: {e}")
        return False


async def main():
    logger.info("=== STARTING OPTIONAL AI SERVICES CHECKS ===")
    
    embed_ok = await check_embeddings()
    chroma_ok = await check_chromadb()
    llm_ok = await check_llm_provider()
    
    logger.info("============================================")
    if embed_ok and chroma_ok and llm_ok:
        logger.info("AI SERVICES VERIFICATION: SUCCESS (AI services ready/mocked)")
        sys.exit(0)
    else:
        logger.error("AI SERVICES VERIFICATION: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
