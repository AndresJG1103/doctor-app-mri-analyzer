"""Pydantic schemas for API request and response models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================


class ProcessingType(str, Enum):
    """Type of FastSurfer processing to perform."""

    SEG_ONLY = "seg_only"  # Segmentation only (~5 min GPU)
    SURF_ONLY = "surf_only"  # Surface reconstruction only (~60-90 min)
    FULL = "full"  # Full pipeline (segmentation + surface)


class JobStatus(str, Enum):
    """Status of a processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Processing Options
# =============================================================================


class ProcessingOptions(BaseModel):
    """Options for MRI processing."""

    model_config = ConfigDict(extra="forbid")

    threads: int = Field(
        default=4, ge=1, le=32, description="Number of threads for processing"
    )
    use_3T_atlas: bool = Field(
        default=True,
        description="Use 3T atlas instead of 1.5T (better for 3T scanners)",
    )
    no_biasfield: bool = Field(
        default=False, description="Skip bias field correction"
    )
    no_cereb: bool = Field(
        default=False, description="Skip cerebellum sub-segmentation"
    )
    no_hypothal: bool = Field(
        default=False, description="Skip hypothalamus segmentation"
    )
    vox_size: str = Field(
        default="min",
        description="Voxel size: 'min' (auto) or value between 0.7 and 1.0",
    )


# =============================================================================
# Request Schemas
# =============================================================================


class MRIProcessRequest(BaseModel):
    """Request schema for MRI processing endpoint (form data)."""

    model_config = ConfigDict(extra="forbid")

    processing_type: ProcessingType = Field(
        ..., description="Type of processing: seg_only, surf_only, or full"
    )
    subject_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Subject ID (auto-generated if not provided)",
    )
    options: ProcessingOptions = Field(
        default_factory=ProcessingOptions, description="Processing options"
    )


# =============================================================================
# Response Schemas
# =============================================================================


class JobCreateResponse(BaseModel):
    """Response when a job is created."""

    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    subject_id: str = Field(..., description="Subject identifier")
    processing_type: ProcessingType = Field(..., description="Type of processing")
    created_at: datetime = Field(..., description="Job creation timestamp")
    message: str = Field(..., description="Status message")


class JobStatusResponse(BaseModel):
    """Response with job status details."""

    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    subject_id: str = Field(..., description="Subject identifier")
    processing_type: ProcessingType = Field(..., description="Type of processing")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: datetime | None = Field(None, description="Processing start time")
    completed_at: datetime | None = Field(None, description="Processing completion time")
    progress: int = Field(
        default=0, ge=0, le=100, description="Processing progress percentage"
    )
    error_message: str | None = Field(None, description="Error message if failed")
    output_path: str | None = Field(None, description="Path to output files")
    input_file: str = Field(..., description="Original input filename")


class JobListResponse(BaseModel):
    """Response with list of jobs."""

    model_config = ConfigDict(from_attributes=True)

    jobs: list[JobStatusResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=10, description="Items per page")


class JobResultResponse(BaseModel):
    """Response with job results."""

    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    subject_id: str = Field(..., description="Subject identifier")
    output_path: str = Field(..., description="Path to output directory")
    files: list[str] = Field(..., description="List of output files")
    statistics: dict[str, Any] | None = Field(
        None, description="Volume statistics if available"
    )


# =============================================================================
# Health Check Schemas
# =============================================================================


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server timestamp")
    services: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Status of dependent services"
    )


class ServiceHealth(BaseModel):
    """Health status of a service."""

    status: str = Field(..., description="Service status")
    latency_ms: float | None = Field(None, description="Response latency in ms")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")


# =============================================================================
# Error Schemas
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
