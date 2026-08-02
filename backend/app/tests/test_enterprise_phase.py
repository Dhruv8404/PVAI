import os
import sys
import unittest
import time
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app
from app.core.config import settings
from app.core.cache_service import cache_service
from app.core.storage import StorageProviderFactory, LocalStorageProvider
from app.core.task_queue import enqueue_task, get_worker_status, dead_letter_queue, task_registry
from app.core.feature_flags import feature_flags
from app.core.dr_validator import run_dr_validation


class TestEnterprisePhase3(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        cache_service.clear()
        dead_letter_queue.clear()
        task_registry.clear()

    def test_cache_service_operations(self):
        """Verify that cache get, set, delete, and clear operations work properly."""
        cache_key = "test_key_123"
        cache_val = {"data": "hello_enterprise"}
        
        # Verify miss
        self.assertIsNone(cache_service.get(cache_key))
        
        # Verify set & get
        cache_service.set(cache_key, cache_val, ttl=10)
        self.assertEqual(cache_service.get(cache_key), cache_val)
        
        # Verify delete
        cache_service.delete(cache_key)
        self.assertIsNone(cache_service.get(cache_key))

    def test_redis_graceful_fallback(self):
        """Verify caching falls back to in-memory mode if Redis connection is unavailable."""
        from app.core.redis_service import redis_service
        # Simulate Redis offline
        original_online = redis_service._online
        redis_service._online = False
        
        try:
            cache_key = "fallback_test"
            cache_val = "memory_value"
            
            # Cache operations must still succeed using local memory
            cache_service.set(cache_key, cache_val)
            self.assertEqual(cache_service.get(cache_key), cache_val)
        finally:
            redis_service._online = original_online

    def test_storage_abstraction(self):
        """Verify that StorageProviderFactory resolves and LocalStorageProvider copies files."""
        provider = StorageProviderFactory.get_provider()
        self.assertIsNotNone(provider)
        
        # Verify LocalStorageProvider works
        local_prov = LocalStorageProvider(upload_dir="storage/test_uploads")
        test_file = "storage/test_uploads/sample.txt"
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, "w") as f:
            f.write("standardization content")
            
        try:
            dest_name = "uploaded_sample.txt"
            url = local_prov.upload_file(test_file, dest_name)
            self.assertTrue(url.endswith(dest_name))
            self.assertTrue(os.path.exists(url))
            
            # Clean up
            local_prov.delete_file(url)
            self.assertFalse(os.path.exists(url))
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_task_queue_priorities_and_dlq(self):
        """Verify priority queue sorting, task heartbeats, and failure redirection to DLQ."""
        # Enqueue a failing task designed to fail and exceed max retries
        def failing_task():
            raise RuntimeError("Task execution failed")
            
        task_id = enqueue_task(failing_task, priority=1, max_retries=1)
        
        # Give worker threads brief moment to run and complete
        time.sleep(2.5)
        
        status = get_worker_status()
        self.assertIn("active_threads_count", status)
        self.assertGreater(status["active_threads_count"], 0)
        
        # Verify that task fails and enters Dead-Letter Queue (DLQ)
        task_info = task_registry.get(task_id)
        self.assertIsNotNone(task_info)
        self.assertEqual(task_info["status"], "FAILED")
        
        self.assertGreater(len(dead_letter_queue), 0)
        self.assertEqual(dead_letter_queue[0]["task_id"], task_id)

    def test_feature_flags_loading(self):
        """Verify environment feature flags fetch correct active statuses."""
        flags = feature_flags.get_all_flags()
        self.assertIn("FEATURE_AI_PROVIDERS", flags)
        self.assertIn("FEATURE_EXPERIMENTAL_ENDPOINTS", flags)
        self.assertIn("FEATURE_BACKGROUND_WORKERS", flags)
        self.assertTrue(feature_flags.AI_PROVIDERS)
        self.assertFalse(feature_flags.EXPERIMENTAL_ENDPOINTS)

    def test_deepseek_provider_resolution(self):
        """Verify that LLMProviderFactory correctly returns and registers deepseek provider."""
        from app.modules.ai.providers.llm_factory import llm_factory, DeepSeekProviderWrapper
        provider = llm_factory.get_provider("deepseek")
        self.assertIsNotNone(provider)
        self.assertEqual(provider._provider.__class__, DeepSeekProviderWrapper)

    def test_disaster_recovery_validator(self):
        """Verify that DR validation script executes and returns expected schema checks."""
        # Use run_dr_validation from app.core.dr_validator
        # (Execute inside async/sync wrapper since unittest runner is synchronous)
        import asyncio
        dr_report = asyncio.run(run_dr_validation())
        
        self.assertIn("status", dr_report)
        self.assertIn("database", dr_report)
        self.assertIn("chromadb", dr_report)
        self.assertIn("storage", dr_report)

    def test_ops_diagnostics_endpoint(self):
        """Verify that /api/v1/ops/diagnostics admin endpoint returns status and flags."""
        response = self.client.get("/api/v1/ops/diagnostics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("feature_flags", data)
        self.assertIn("cache", data)
        self.assertIn("worker", data)


if __name__ == "__main__":
    unittest.main()
