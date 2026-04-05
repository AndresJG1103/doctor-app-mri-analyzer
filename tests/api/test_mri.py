"""Tests for MRI processing endpoints."""

import io
import os
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest
from fastapi.testclient import TestClient


class TestMRIProcessEndpoint:
    """Test suite for MRI processing endpoint."""

    def test_process_mri_requires_file(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that /mri/process requires a file."""
        response = client.post(
            "/api/v1/mri/process",
            data={"processing_type": "seg_only"},
            headers=auth_headers,
        )
        
        assert response.status_code == 422  # Validation error

    def test_process_mri_validates_file_extension(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that only valid file extensions are accepted."""
        # Create a fake file with invalid extension
        fake_file = io.BytesIO(b"fake content")
        
        response = client.post(
            "/api/v1/mri/process",
            data={"processing_type": "seg_only"},
            files={"file": ("test.txt", fake_file, "text/plain")},
            headers=auth_headers,
        )
        
        assert response.status_code == 400
        assert "Invalid file extension" in response.json()["detail"]

    def test_process_mri_accepts_nii_gz(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that .nii.gz files are accepted."""
        # Create a minimal gzip file
        import gzip
        import io
        
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
            gz.write(b"\x00" * 100)
        buffer.seek(0)
        
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.create_job.return_value = MagicMock(
                job_id="test-123",
                status="queued",
                subject_id="test_subject",
                processing_type="seg_only",
                created_at=datetime.utcnow(),
                message="Job enqueued successfully",
            )
            
            with patch("aiofiles.open", create=True):
                with patch("aiofiles.threadpool.sync_open"):
                    response = client.post(
                        "/api/v1/mri/process",
                        data={"processing_type": "seg_only"},
                        files={"file": ("brain.nii.gz", buffer, "application/gzip")},
                        headers=auth_headers,
                    )
        
        # Should either succeed or fail on file save (not validation)
        assert response.status_code in [202, 500]

    def test_process_mri_validates_processing_type(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that processing_type is validated."""
        fake_file = io.BytesIO(b"fake content")
        
        response = client.post(
            "/api/v1/mri/process",
            data={"processing_type": "invalid_type"},
            files={"file": ("test.nii.gz", fake_file, "application/gzip")},
            headers=auth_headers,
        )
        
        assert response.status_code == 422

    def test_process_mri_sanitizes_subject_id(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that subject_id is sanitized."""
        import gzip
        import io
        
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as gz:
            gz.write(b"\x00" * 100)
        buffer.seek(0)
        
        # Subject ID with path traversal attempt
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.create_job.return_value = MagicMock(
                job_id="test-123",
                status="queued",
                subject_id="testsafe",  # Sanitized
                processing_type="seg_only",
                created_at=datetime.utcnow(),
                message="Job enqueued successfully",
            )
            
            with patch("aiofiles.open", create=True):
                response = client.post(
                    "/api/v1/mri/process",
                    data={
                        "processing_type": "seg_only",
                        "subject_id": "../../../etc/passwd",
                    },
                    files={"file": ("brain.nii.gz", buffer, "application/gzip")},
                    headers=auth_headers,
                )
        
        # Should sanitize the subject_id
        if response.status_code == 202:
            # Verify sanitization happened
            call_args = mock_jm.create_job.call_args
            assert ".." not in str(call_args)


class TestJobListEndpoint:
    """Test suite for job list endpoint."""

    def test_list_jobs_returns_empty_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that list jobs returns empty list when no jobs exist."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.list_jobs.return_value = MagicMock(
                jobs=[],
                total=0,
                page=1,
                page_size=10,
            )
            
            response = client.get("/api/v1/mri/jobs", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["jobs"] == []
            assert data["total"] == 0

    def test_list_jobs_with_pagination(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test pagination parameters."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.list_jobs.return_value = MagicMock(
                jobs=[],
                total=0,
                page=2,
                page_size=5,
            )
            
            response = client.get(
                "/api/v1/mri/jobs?page=2&page_size=5", headers=auth_headers
            )
            
            assert response.status_code == 200
            mock_jm.list_jobs.assert_called_once_with(
                page=2, page_size=5, status_filter=None
            )

    def test_list_jobs_with_status_filter(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test filtering by status."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.list_jobs.return_value = MagicMock(
                jobs=[],
                total=0,
                page=1,
                page_size=10,
            )
            
            response = client.get(
                "/api/v1/mri/jobs?status_filter=completed", headers=auth_headers
            )
            
            assert response.status_code == 200


class TestJobStatusEndpoint:
    """Test suite for job status endpoint."""

    def test_get_job_returns_404_for_nonexistent(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that getting a non-existent job returns 404."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.get_job.return_value = None
            
            response = client.get(
                "/api/v1/mri/jobs/nonexistent-id", headers=auth_headers
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_job_returns_status(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that getting an existing job returns its status."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.get_job.return_value = MagicMock(
                job_id="test-123",
                status="processing",
                subject_id="test_subject",
                processing_type="seg_only",
                created_at=datetime.utcnow(),
                started_at=datetime.utcnow(),
                completed_at=None,
                progress=50,
                error_message=None,
                output_path=None,
                input_file="test.nii.gz",
            )
            
            response = client.get("/api/v1/mri/jobs/test-123", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-123"
            assert data["status"] == "processing"
            assert data["progress"] == 50


class TestCancelJobEndpoint:
    """Test suite for cancel job endpoint."""

    def test_cancel_job_returns_404_for_nonexistent(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that cancelling a non-existent job returns 404."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.get_job.return_value = None
            
            response = client.delete(
                "/api/v1/mri/jobs/nonexistent-id", headers=auth_headers
            )
            
            assert response.status_code == 404

    def test_cancel_job_only_works_for_queued(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that only queued jobs can be cancelled."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.get_job.return_value = MagicMock(
                job_id="test-123",
                status="processing",  # Not queued
            )
            
            response = client.delete("/api/v1/mri/jobs/test-123", headers=auth_headers)
            
            assert response.status_code == 400
            assert "cannot cancel" in response.json()["detail"].lower()

    def test_cancel_queued_job_succeeds(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Test that cancelling a queued job succeeds."""
        with patch("app.api.v1.endpoints.mri.job_manager") as mock_jm:
            mock_jm.get_job.return_value = MagicMock(
                job_id="test-123",
                status="queued",
            )
            mock_jm.cancel_job.return_value = True
            
            response = client.delete("/api/v1/mri/jobs/test-123", headers=auth_headers)
            
            assert response.status_code == 204
