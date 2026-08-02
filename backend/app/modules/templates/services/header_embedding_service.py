import logging
from typing import List
from app.modules.templates.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class HeaderEmbeddingService:
    def generate_header_embedding(self, text: str) -> List[float]:
        """Wrapper service that utilizes BAAI/bge-small-en-v1.5 to vectorize an Excel header."""
        logger.debug(f"Generating embedding vector for header: '{text}'")
        return embedding_service.generate_embedding(text)


header_embedding_service = HeaderEmbeddingService()
