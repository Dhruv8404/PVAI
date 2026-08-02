import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from app.modules.ai.embeddings.embedding_service import embedding_service as ai_embedding_service
from app.modules.ai.vector_db.chroma_service import chroma_service as ai_chroma_service

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, persist_directory: str = "storage/chromadb"):
        self.persist_directory = persist_directory
        self._mock_db: Dict[str, Dict[str, Any]] = {}  # In-memory fallback dictionary for tests or mock operations
        
    def _get_model(self):
        """Returns the pre-loaded local embedding model instance."""
        return ai_embedding_service._model

    def _get_chroma_client(self):
        """Returns the pre-initialized ChromaDB PersistentClient."""
        return ai_chroma_service._client

    def _get_collection(self, collection_name: str = "template_fields"):
        """Gets or creates the template fields ChromaDB collection."""
        try:
            return ai_chroma_service.get_or_create_collection(collection_name)
        except Exception as e:
            logger.error(f"Failed to delegate collection fetch: {e}")
            return None

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a 384-dimensional vector embedding for the given text."""
        return ai_embedding_service.generate_embedding(text)

    def store_field_embedding(
        self, 
        template_id: str, 
        field_name: str, 
        embedding: List[float], 
        metadata: Dict[str, Any]
    ) -> str:
        """Stores embedding vector in ChromaDB with metadata. Returns document ID."""
        doc_id = f"{template_id}_{field_name.replace(' ', '_')}"
        
        # Format template_id and ensure metadata is correct
        metadata_clean = {k: str(v) if isinstance(v, (uuid.UUID, int, float)) else v for k, v in metadata.items()}
        metadata_clean["template_id"] = str(template_id)
        
        try:
            ai_chroma_service.upsert(
                collection_name="template_fields",
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata_clean],
                documents=[field_name]
            )
            logger.info(f"[ChromaDB Delegated] Stored embedding for field '{field_name}' in template '{template_id}'. ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.warning(f"ChromaDB delegated store failed: {e}. Falling back to local mock DB.")
            
        # In-memory fallback storage
        self._mock_db[doc_id] = {
            "template_id": str(template_id),
            "field_name": field_name,
            "embedding": embedding,
            "metadata": metadata_clean
        }
        logger.info(f"[MockDB] Stored embedding for field '{field_name}' in template '{template_id}'. ID: {doc_id}")
        return doc_id

    def delete_template_embeddings(self, template_id: str) -> None:
        """Wipes all field embeddings belonging to the specified template_id."""
        template_id_str = str(template_id)
        
        try:
            ai_chroma_service.delete(
                collection_name="template_fields",
                where={"template_id": template_id_str}
            )
            logger.info(f"[ChromaDB Delegated] Deleted all embeddings for template_id: {template_id_str}")
        except Exception as e:
            logger.warning(f"ChromaDB delegated delete failed: {e}.")
        
        # Wiping from mock storage
        keys_to_delete = [
            k for k, v in self._mock_db.items() 
            if str(v.get("metadata", {}).get("template_id")) == template_id_str 
            or str(v.get("template_id")) == template_id_str
        ]
        for k in keys_to_delete:
            del self._mock_db[k]
        logger.info(f"[MockDB] Deleted all embeddings for template_id: {template_id_str}")


embedding_service = EmbeddingService()
