import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app
from app.core.config import settings


class TestProductionPhase2(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_security_headers_injection(self):
        """Verify that the SecurityHeadersMiddleware injects secure headers on all responses."""
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        
        # Verify Headers
        headers = response.headers
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("Permissions-Policy", headers)
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy"))

    def test_request_id_correlation(self):
        """Verify that the RequestIDMiddleware injects a correlation UUID X-Request-ID."""
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        
        # 1. Verify header generation
        self.assertIn("X-Request-ID", response.headers)
        req_id_1 = response.headers.get("X-Request-ID")
        self.assertGreater(len(req_id_1), 10)
        
        # 2. Verify header propagation if passed
        custom_req_id = "test-correlation-id-9999"
        response2 = self.client.get("/health/live", headers={"X-Request-ID": custom_req_id})
        self.assertEqual(response2.headers.get("X-Request-ID"), custom_req_id)

    def test_gzip_performance_compression(self):
        """Verify GZipMiddleware compresses payloads larger than 1KB when accepted."""
        # Create a large text response payload (more than 1024 bytes)
        # Querying an endpoint that returns a large payload, e.g., /health/full
        response = self.client.get("/health/full", headers={"Accept-Encoding": "gzip"})
        # Gzip compression depends on response size. If body size is > 1024, it will be compressed
        if len(response.content) > 1024:
            self.assertEqual(response.headers.get("Content-Encoding"), "gzip")

    def test_health_endpoints_split(self):
        """Verify liveness, readiness, and full diagnostics health splits function correctly."""
        # 1. Live Check
        response_live = self.client.get("/health/live")
        self.assertEqual(response_live.status_code, 200)
        self.assertEqual(response_live.json(), {"status": "healthy"})
        
        # 2. Ready Check
        response_ready = self.client.get("/health/ready")
        self.assertIn(response_ready.status_code, [200, 503])
        data_ready = response_ready.json()
        self.assertIn("status", data_ready)
        self.assertIn("database", data_ready)
        self.assertIn("storage", data_ready)

        # 3. Full Check
        response_full = self.client.get("/health/full")
        self.assertIn(response_full.status_code, [200, 503])
        data_full = response_full.json()
        self.assertIn("status", data_full)
        self.assertIn("worker", data_full)
        self.assertIn("uptime", data_full)

    def test_metrics_endpoint_scraping(self):
        """Verify `/metrics` endpoint is working and returns plain text format."""
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn("http_active_requests", response.text)


if __name__ == "__main__":
    unittest.main()
