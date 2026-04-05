"""Tests for authentication."""

import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestAuthentication:
    """Test suite for HTTP Basic Authentication."""

    def _auth_header(self, username: str, password: str) -> dict[str, str]:
        """Create HTTP Basic Auth header."""
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    def test_mri_endpoints_require_auth(self, client: TestClient) -> None:
        """Test that MRI endpoints return 401 without credentials."""
        # Test various MRI endpoints without auth
        endpoints = [
            ("GET", "/api/v1/mri/jobs"),
            ("GET", "/api/v1/mri/jobs/some-id"),
            ("DELETE", "/api/v1/mri/jobs/some-id"),
        ]
        
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path)
            elif method == "DELETE":
                response = client.delete(path)
            
            assert response.status_code == 401, f"{method} {path} should require auth"
            assert response.headers.get("WWW-Authenticate") == "Basic"

    def test_invalid_credentials_returns_401(self, client: TestClient) -> None:
        """Test that invalid credentials return 401."""
        headers = self._auth_header("wrong_user", "wrong_pass")
        
        response = client.get("/api/v1/mri/jobs", headers=headers)
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_valid_credentials_allow_access(self, client: TestClient) -> None:
        """Test that valid credentials allow access to protected endpoints."""
        # Use default credentials from settings
        headers = self._auth_header("admin", "changeme")
        
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.list_jobs.return_value = MagicMock(
                jobs=[],
                total=0,
                page=1,
                page_size=10,
            )
            
            response = client.get("/api/v1/mri/jobs", headers=headers)
            
            assert response.status_code == 200

    def test_health_endpoints_do_not_require_auth(self, client: TestClient) -> None:
        """Test that health endpoints are accessible without authentication."""
        # Health check
        with patch("app.api.v1.endpoints.health.redis_client") as mock_redis:
            mock_redis.health_check.return_value = {"status": "healthy"}
            mock_redis.is_connected.return_value = True
            
            with patch("app.api.v1.endpoints.health.fastsurfer_service") as mock_fs:
                mock_fs.health_check.return_value = {"status": "healthy"}
                
                response = client.get("/api/v1/health")
                assert response.status_code == 200
        
        # Liveness
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        
        # Readiness
        with patch("app.api.v1.endpoints.health.redis_client") as mock_redis:
            mock_redis.is_connected.return_value = True
            
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 200

    def test_root_endpoint_does_not_require_auth(self, client: TestClient) -> None:
        """Test that root endpoint is accessible without authentication."""
        response = client.get("/")
        
        assert response.status_code == 200

    def test_partial_credentials_return_401(self, client: TestClient) -> None:
        """Test that partial/malformed credentials return 401."""
        # Only username correct
        headers = self._auth_header("admin", "wrong_password")
        response = client.get("/api/v1/mri/jobs", headers=headers)
        assert response.status_code == 401
        
        # Only password correct
        headers = self._auth_header("wrong_user", "changeme")
        response = client.get("/api/v1/mri/jobs", headers=headers)
        assert response.status_code == 401

    def test_empty_credentials_return_401(self, client: TestClient) -> None:
        """Test that empty credentials return 401."""
        headers = self._auth_header("", "")
        
        response = client.get("/api/v1/mri/jobs", headers=headers)
        
        assert response.status_code == 401


class TestSecurityModule:
    """Test suite for the security module functions."""

    def test_verify_credentials_with_valid_credentials(self) -> None:
        """Test verify_credentials returns True for valid credentials."""
        from app.core.security import verify_credentials
        
        # Uses default settings values
        assert verify_credentials("admin", "changeme") is True

    def test_verify_credentials_with_invalid_credentials(self) -> None:
        """Test verify_credentials returns False for invalid credentials."""
        from app.core.security import verify_credentials
        
        assert verify_credentials("wrong", "credentials") is False
        assert verify_credentials("admin", "wrong") is False
        assert verify_credentials("wrong", "changeme") is False

    def test_verify_credentials_timing_attack_resistance(self) -> None:
        """Test that verify_credentials uses constant-time comparison."""
        import time
        from app.core.security import verify_credentials
        
        # This is a basic sanity check - timing attacks are hard to test definitively
        # The main protection is using secrets.compare_digest() in the implementation
        
        iterations = 100
        
        # Time with completely wrong credentials
        start = time.perf_counter()
        for _ in range(iterations):
            verify_credentials("x", "x")
        wrong_time = time.perf_counter() - start
        
        # Time with almost correct credentials
        start = time.perf_counter()
        for _ in range(iterations):
            verify_credentials("admin", "changem")
        almost_time = time.perf_counter() - start
        
        # Times should be roughly similar (within 50% of each other)
        # This is a weak test but ensures the function doesn't short-circuit
        ratio = max(wrong_time, almost_time) / max(min(wrong_time, almost_time), 0.0001)
        assert ratio < 3, "Timing difference too large, possible timing attack vulnerability"
