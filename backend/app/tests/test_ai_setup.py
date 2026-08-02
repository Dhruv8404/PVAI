import os
import sys
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend app folder to path for import safety
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.modules.ai.embeddings.embedding_service import embedding_service
from app.modules.ai.vector_db.chroma_service import chroma_service
from app.modules.ai.providers.omniroute_provider import omniroute_provider
from app.modules.ai.providers.llm_factory import llm_factory
from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class TestAISetup(unittest.TestCase):
    def test_embedding_model_setup(self):
        """Verify that local embedding service loads and generates correct dimension vector."""
        # Ensure loaded status
        embedding_service.load_model()
        
        # Generate vector
        vector = embedding_service.generate_embedding("safety event report")
        self.assertEqual(len(vector), 384)
        self.assertTrue(all(isinstance(val, float) for val in vector))

    @unittest.skipIf(not HAS_CHROMADB, "ChromaDB library is not installed")
    def test_chromadb_operations(self):
        """Verify that ChromaDB insert, search and delete operations function correctly."""
        # Initialize ChromaDB client
        chroma_service.initialize()
        
        # Ensure collections can be retrieved/created
        col = chroma_service.get_or_create_collection("test_smoke_collection")
        self.assertIsNotNone(col)
        
        # Upsert test vector
        test_id = "test_doc_1"
        test_vector = [0.1] * 384
        test_metadata = {"template_id": "test_tpl", "field": "severity"}
        test_doc = "Severity Description"
        
        chroma_service.upsert(
            collection_name="test_smoke_collection",
            ids=[test_id],
            embeddings=[test_vector],
            metadatas=[test_metadata],
            documents=[test_doc]
        )
        
        # Query vector
        results = chroma_service.query(
            collection_name="test_smoke_collection",
            query_embeddings=[[0.1] * 384],
            n_results=1,
            where={"template_id": "test_tpl"}
        )
        
        self.assertIsNotNone(results)
        self.assertIn("ids", results)
        self.assertGreater(len(results["ids"]), 0)
        self.assertEqual(results["ids"][0][0], test_id)
        
        # Clean up / Delete vector
        chroma_service.delete(
            collection_name="test_smoke_collection",
            ids=[test_id]
        )
        
        # Delete collection
        chroma_service.delete_collection("test_smoke_collection")

    @patch("httpx.AsyncClient.request", new_callable=AsyncMock)
    def test_omniroute_provider_and_factory(self, mock_request):
        """Verify OmniRoute client validation, generate, chat and factory routing works."""
        # Test default provider retrieval
        provider = llm_factory.get_provider("omniroute")
        self.assertIsNotNone(provider)
        
        # Explicitly configure mock credentials on the singleton instance for isolation
        omniroute_provider.api_key = "mock_api_key"
        omniroute_provider.base_url = "http://localhost:20128/v1"
        
        # Set up a side effect for the async client request
        def mock_request_side_effect(method, url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            url_str = str(url)
            if method == "GET" and "/models" in url_str:
                mock_resp.json.return_value = {"data": []}
            elif method == "POST" and "/chat/completions" in url_str:
                mock_resp.json.return_value = {
                    "choices": [{
                        "message": {
                            "content": "Simulated OmniRoute output narrative"
                        }
                    }]
                }
            else:
                mock_resp.json.return_value = {}
            return mock_resp
            
        mock_request.side_effect = mock_request_side_effect
        
        # 1. Test validation mock
        validated = asyncio.run(provider.validate())
        self.assertTrue(validated)
        
        # 2. Test generate mock
        output = asyncio.run(provider.generate(prompt="Explain benefit risk ratio", model="gpt-4o"))
        self.assertEqual(output, "Simulated OmniRoute output narrative")
        
        # 3. Test chat mock
        chat_output = asyncio.run(provider.chat(
            messages=[{"role": "user", "content": "map safety fields"}],
            model="gpt-4o",
            response_format={"type": "json_object"}
        ))
        self.assertEqual(chat_output, "Simulated OmniRoute output narrative")

    def test_health_endpoint_response(self):
        """Verify GET /health returns structured diagnostics JSON schema."""
        client = TestClient(app)
        response = client.get("/health")
        self.assertIn(response.status_code, [200, 503])
        
        data = response.json()
        
        # Assert JSON structure matches the required rich diagnostics
        self.assertIn("status", data)
        self.assertIn("database", data)
        self.assertIn("status", data["database"])
        
        self.assertIn("chromadb", data)
        self.assertIn("status", data["chromadb"])
        self.assertIn("collections", data["chromadb"])
        
        self.assertIn("embedding", data)
        self.assertIn("status", data["embedding"])
        self.assertIn("model", data["embedding"])
        
        self.assertIn("llm", data)
        self.assertIn("provider", data["llm"])
        self.assertIn("status", data["llm"])
        
        self.assertIn("storage", data)
        self.assertIn("status", data["storage"])
        
        self.assertIn("version", data)


if __name__ == "__main__":
    unittest.main()
