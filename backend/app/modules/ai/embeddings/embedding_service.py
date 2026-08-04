import logging
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    def __init__(self):
        self._model = None
        self._loaded = False

    def load_model(self):
        """Loads the SentenceTransformer model once during application startup."""
        if self._loaded:
            return
        
        model_name = settings.EMBEDDING_MODEL
        logger.info(f"Loading local embedding model: {model_name}...")
        
        # Check system memory to prevent OOM crash on memory-constrained servers (e.g. Render 512MB RAM)
        try:
            import psutil
            total_ram = psutil.virtual_memory().total
            if total_ram < 1.5 * 1024 * 1024 * 1024:
                logger.warning(f"System memory ({total_ram / (1024*1024):.0f}MB) is insufficient to safely load PyTorch model. Using deterministic mock vector fallback.")
                self._loaded = False
                self._model = None
                return
        except Exception:
            pass

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            self._loaded = True
            logger.info(f"Embedding model '{model_name}' loaded successfully.")
        except (ImportError, MemoryError, Exception) as e:
            logger.error(f"Failed to load sentence-transformers model '{model_name}': {e}. Graceful mock embeddings fallback will be used.")
            self._loaded = False
            self._model = None

    def is_loaded(self) -> bool:
        """Returns True if the embedding model is loaded."""
        return self._loaded and self._model is not None

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a float list embedding vector for the given text (384 dimensions for BGE-small)."""
        if self.is_loaded():
            try:
                embeddings = self._model.encode([text], normalize_embeddings=True)
                return [float(x) for x in embeddings[0]]
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}. Falling back to mock vector.")
        
        # Fallback deterministic mock (384 dimensions)
        return self._generate_mock_embedding(text)

    def generate_embeddings(self, list_of_text: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text inputs."""
        if self.is_loaded():
            try:
                embeddings = self._model.encode(list_of_text, normalize_embeddings=True)
                return [[float(x) for x in emb] for emb in embeddings]
            except Exception as e:
                logger.error(f"Batch embedding generation failed: {e}. Falling back to mock vectors.")
                
        return [self._generate_mock_embedding(txt) for txt in list_of_text]

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generates a deterministic mock embedding vector of 384 dimensions."""
        import hashlib
        import math
        sha = hashlib.sha256(text.encode("utf-8")).digest()
        result = []
        for i in range(384):
            val = sha[(i % len(sha))] * ((i + 1) * 0.13)
            result.append(float(math.sin(val)))
        return result


embedding_service = LocalEmbeddingService()
