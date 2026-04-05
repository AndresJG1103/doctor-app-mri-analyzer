"""Pytest configuration and fixtures."""

import base64
import os
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["DATA_INPUT_DIR"] = tempfile.mkdtemp()
os.environ["DATA_OUTPUT_DIR"] = tempfile.mkdtemp()
os.environ["AUTH_USERNAME"] = "admin"
os.environ["AUTH_PASSWORD"] = "changeme"


def _auth_header(username: str = "admin", password: str = "changeme") -> dict[str, str]:
    """Create HTTP Basic Auth header with default test credentials."""
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture(scope="session")
def mock_redis() -> MagicMock:
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.set.return_value = True
    mock.get.return_value = None
    mock.zadd.return_value = 1
    mock.rpush.return_value = 1
    mock.llen.return_value = 0
    mock.zcard.return_value = 0
    mock.zrevrange.return_value = []
    mock.info.return_value = {"redis_version": "7.0.0"}
    return mock


@pytest.fixture(scope="function")
def client(mock_redis: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""
    with patch("app.core.redis.redis_client._client", mock_redis):
        with patch("app.core.redis.redis_client.connect", return_value=mock_redis):
            with patch("app.core.redis.redis_client.is_connected", return_value=True):
                # Import app after patching
                from app.main import app
                
                with TestClient(app) as test_client:
                    yield test_client


@pytest.fixture(scope="function")
def auth_client(client: TestClient) -> Generator[TestClient, None, None]:
    """
    Create an authenticated test client.
    
    Wraps the client to include auth headers in all requests.
    """
    original_request = client.request
    
    def authenticated_request(method: str, url: str, **kwargs) -> any:
        headers = kwargs.pop("headers", {})
        headers.update(_auth_header())
        return original_request(method, url, headers=headers, **kwargs)
    
    client.request = authenticated_request
    yield client
    client.request = original_request


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return valid authentication headers for tests."""
    return _auth_header()


@pytest.fixture
def sample_nii_file() -> Generator[str, None, None]:
    """Create a sample .nii.gz file for testing."""
    import gzip
    
    # Create a minimal NIfTI-like file (just for testing file upload)
    with tempfile.NamedTemporaryFile(suffix=".nii.gz", delete=False) as f:
        # Write minimal gzip content
        with gzip.open(f.name, "wb") as gz:
            # Write some dummy NIfTI header bytes
            gz.write(b"\x00" * 348)  # Minimal NIfTI header size
        
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def mock_fastsurfer_service() -> Generator[MagicMock, None, None]:
    """Mock the FastSurfer service."""
    with patch("app.services.fastsurfer.fastsurfer_service") as mock:
        mock.health_check.return_value = {
            "status": "healthy",
            "docker": "connected",
            "image_available": True,
            "image": "deepmi/fastsurfer:latest",
            "gpu_enabled": False,
        }
        mock.is_available.return_value = True
        mock.process_mri.return_value = {
            "success": True,
            "output_path": "/data/output/test_subject",
            "message": "Processing completed successfully",
        }
        yield mock


@pytest.fixture
def mock_job_manager(mock_redis: MagicMock) -> Generator[MagicMock, None, None]:
    """Mock the job manager."""
    with patch("app.services.job_manager.job_manager") as mock:
        mock.create_job.return_value = MagicMock(
            job_id="test-job-123",
            status="queued",
            subject_id="test_subject",
            processing_type="seg_only",
            created_at="2026-02-27T00:00:00Z",
            message="Job enqueued successfully",
        )
        mock.get_job.return_value = None
        mock.list_jobs.return_value = MagicMock(
            jobs=[],
            total=0,
            page=1,
            page_size=10,
        )
        yield mock
