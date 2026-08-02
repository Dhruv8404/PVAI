import logging
import math
import uuid
from typing import List, Dict, Any, Tuple
from app.modules.templates.services.embedding_service import embedding_service
from app.modules.templates.model import AIConfiguration

logger = logging.getLogger(__name__)


def compute_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Helper to compute cosine similarity manually for fallback operations."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(a * a for a in v1))
    magnitude_v2 = math.sqrt(sum(a * a for a in v2))
    if magnitude_v1 == 0.0 or magnitude_v2 == 0.0:
        return 0.0
    return dot_product / (magnitude_v1 * magnitude_v2)


class HeaderSimilarityService:
    def find_nearest_fields(
        self, 
        template_id: uuid.UUID, 
        header_name: str, 
        header_embedding: List[float],
        ai_config: AIConfiguration
    ) -> List[Dict[str, Any]]:
        """Queries the template fields collection for matches against a header embedding.
        
        Returns a sorted list of matches:
        [
            {
                "field_name": "Patient Name",
                "similarity": 0.94,
                "required": True,
                "status": "AutoMapped",
                "source": "Embedding"
            },
            ...
        ]
        """
        logger.info(f"Querying nearest fields in ChromaDB for header: '{header_name}'")
        template_id_str = str(template_id)
        collection = embedding_service._get_collection()
        matches: List[Tuple[str, float, bool]] = []
        
        if collection:
            try:
                # Query ChromaDB collection
                results = collection.query(
                    query_embeddings=[header_embedding],
                    n_results=5,
                    where={"template_id": template_id_str}
                )
                
                # Check results
                if results and "documents" in results and results["documents"]:
                    documents = results["documents"][0]
                    distances = results["distances"][0] if "distances" in results else [0.0] * len(documents)
                    metadatas = results["metadatas"][0] if "metadatas" in results else [{}] * len(documents)
                    
                    for doc, dist, meta in zip(documents, distances, metadatas):
                        # Cosine similarity = 1 - cosine distance
                        similarity = max(0.0, min(1.0, 1.0 - float(dist)))
                        req = meta.get("required", True)
                        matches.append((doc, similarity, req))
            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}. Fallback to mock search.")
                collection = None  # Force fallback
                
        # Mock database fallback search
        if not collection or not matches:
            logger.info("Performing vector similarity search in mock database...")
            # Query the in-memory fallback dict
            mock_entries = embedding_service._mock_db
            for doc_id, entry in mock_entries.items():
                meta = entry.get("metadata", {})
                entry_tpl_id = str(meta.get("template_id"))
                
                if entry_tpl_id == template_id_str:
                    field_name = entry.get("field_name")
                    entry_vector = entry.get("embedding")
                    similarity = compute_cosine_similarity(header_embedding, entry_vector)
                    req = meta.get("required", True)
                    matches.append((field_name, similarity, req))
            
            # Sort mock results descending by similarity
            matches.sort(key=lambda x: x[1], reverse=True)
            matches = matches[:5]

        # Classify matches according to configured thresholds
        classified_results = []
        for field_name, similarity, req in matches:
            if similarity >= ai_config.similarity_threshold:
                status = "AutoMapped"
                source = "Embedding"
            elif similarity >= ai_config.llm_threshold:
                status = "NeedsLLM"
                source = "Embedding"
            else:
                status = "NeedsReview"
                source = "Manual"
                
            classified_results.append({
                "field_name": field_name,
                "similarity": round(similarity, 4),
                "required": req,
                "status": status,
                "source": source
            })
            
        logger.info(f"Top match for '{header_name}': {classified_results[0] if classified_results else 'None'}")
        return classified_results


header_similarity_service = HeaderSimilarityService()
