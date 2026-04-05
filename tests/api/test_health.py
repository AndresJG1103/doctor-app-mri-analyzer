"""Tests for health check endpoints."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_check_returns_200(self, client: TestClient) -> None:
        """Test that health check endpoint returns 200 OK."""
        with patch("app.api.v1.endpoints.health.redis_client") as mock_redis:
            mock_redis.health_check.return_value = {"status": "healthy", "version": "7.0.0"}
            mock_redis.is_connected.return_value = True
            
            with patch("app.api.v1.endpoints.health.fastsurfer_service") as mock_fs:
                mock_fs.health_check.return_value = {
                    "status": "healthy",
                    "docker": "connected",
                    "image_available": True,
                }
                
                response = client.get("/api/v1/health")
                
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert "version" in data
                assert "timestamp" in data
                assert "services" in data

    def test_health_check_includes_version(self, client: TestClient) -> None:
        """Test that health check includes API version."""
        with patch("app.api.v1.endpoints.health.redis_client") as mock_redis:
            mock_redis.health_check.return_value = {"status": "healthy"}
            
            with patch("app.api.v1.endpoints.health.fastsurfer_service") as mock_fs:
                mock_fs.health_check.return_value = {"status": "healthy"}
                
                response = client.get("/api/v1/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["version"] == "0.1.0"

    def test_liveness_check_returns_200(self, client: TestClient) -> None:
        """Test that liveness endpoint returns 200 OK."""
        response = client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_readiness_check_when_redis_connected(self, client: TestClient) -> None:
        """Test readiness check when Redis is connected."""
        with patch("app.api.v1.endpoints.health.redis_client") as mock_redis:
            mock_redis.is_connected.return_value = True
            
            response = client.get("/api/v1/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"

    def test_readiness_check_when_redis_disconnected(self, client: TestClient) -> None:
        """Test readiness check returns 503 when Redis is not connected."""
        with patch("app.api.v1.endpoints.health.redis_client") as mock_redis:
            mock_redis.is_connected.return_value = False
            
            response = client.get("/api/v1/health/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"

    def test_health_check_reports_degraded_when_redis_unhealthy(
        self, client: TestClient
    ) -> None:
        """Test that health check reports degraded status when Redis is unhealthy."""
        with patch("app.api.v1.endpoints.health.redis_client") as mock_redis:
            mock_redis.health_check.return_value = {
                "status": "unhealthy",
                "error": "Connection refused",
            }
            
            with patch("app.api.v1.endpoints.health.fastsurfer_service") as mock_fs:
                mock_fs.health_check.return_value = {"status": "healthy"}
                
                response = client.get("/api/v1/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
