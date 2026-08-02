import os
import logging
from typing import Dict, Any, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChromaService:
    def __init__(self):
        self._client = None
        self._initialized = False

    def initialize(self, persist_directory: Optional[str] = None):
        """Initializes the PersistentClient for ChromaDB."""
        if self._initialized:
            return
        
        path = persist_directory or settings.CHROMA_DB_PATH
        logger.info(f"Initializing ChromaDB client at path: {path}")
        
        # Ensure path directory exists
        os.makedirs(path, exist_ok=True)
        
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=path)
            self._initialized = True
            logger.info("ChromaDB PersistentClient initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB PersistentClient: {e}")
            self._initialized = False
            raise e

    def is_connected(self) -> bool:
        """Returns True if the ChromaDB client is initialized and connected."""
        if not self._initialized or self._client is None:
            return False
        try:
            # Try a lightweight heartbeat call to verify it's responsive
            self._client.heartbeat()
            return True
        except Exception:
            return False

    def get_or_create_collection(self, collection_name: str):
        """Retrieves or creates a collection by name."""
        if not self._initialized or self._client is None:
            # Auto-initialize if possible
            try:
                self.initialize()
            except Exception:
                raise RuntimeError("ChromaDB client is not initialized and failed to auto-initialize.")
        try:
            collection = self._client.get_or_create_collection(name=collection_name)
            return collection
        except Exception as e:
            logger.error(f"Failed to get or create ChromaDB collection '{collection_name}': {e}")
            raise e

    def delete_collection(self, collection_name: str):
        """Deletes a collection by name."""
        if not self._initialized or self._client is None:
            raise RuntimeError("ChromaDB client is not initialized.")
        try:
            self._client.delete_collection(name=collection_name)
            logger.info(f"Deleted ChromaDB collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB collection '{collection_name}': {e}")
            raise e

    def upsert(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        documents: List[str]
    ):
        """Upserts embeddings, metadata and document text into a collection."""
        collection = self.get_or_create_collection(collection_name)
        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            logger.debug(f"Upserted {len(ids)} documents into ChromaDB collection '{collection_name}'")
        except Exception as e:
            logger.error(f"Upsert failed in collection '{collection_name}': {e}")
            raise e

    def query(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Queries the collection using the input embeddings."""
        collection = self.get_or_create_collection(collection_name)
        try:
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            logger.error(f"Query failed in collection '{collection_name}': {e}")
            raise e

    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ):
        """Deletes items from a collection by ID list or filter dict."""
        collection = self.get_or_create_collection(collection_name)
        try:
            collection.delete(ids=ids, where=where)
            logger.info(f"Deleted items from collection '{collection_name}' with ids: {ids}, where: {where}")
        except Exception as e:
            logger.error(f"Delete failed in collection '{collection_name}': {e}")
            raise e


chroma_service = ChromaService()
