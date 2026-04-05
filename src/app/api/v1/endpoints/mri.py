"""MRI Processing endpoints."""

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from app.core.config import settings
from app.models.schemas import (
    ErrorResponse,
    JobCreateResponse,
    JobListResponse,
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
    ProcessingOptions,
    ProcessingType,
)
from app.services.job_manager import job_manager
from app.services.pdf_generator import PDFGenerator
from app.services.stats_parser import StatsParser
from app.services.volume_extractor import VolumeExtractor

router = APIRouter()


def validate_file_extension(filename: str) -> bool:
    """Validate that the file has an allowed extension."""
    for ext in settings.ALLOWED_EXTENSIONS:
        if filename.lower().endswith(ext):
            return True
    return False


def sanitize_subject_id(subject_id: str) -> str:
    """Sanitize subject ID to prevent path traversal."""
    # Remove any path separators and dangerous characters
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", subject_id)
    return sanitized[:64] if sanitized else None


@router.post(
    "/process",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process MRI File",
    description="Upload an MRI file (.nii.gz) and start processing with FastSurfer",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def process_mri(
    file: Annotated[UploadFile, File(description="MRI file (.nii, .nii.gz, or .mgz)")],
    processing_type: Annotated[
        ProcessingType,
        Form(description="Type of processing: seg_only, surf_only, or full"),
    ],
    subject_id: Annotated[
        str | None,
        Form(
            description="Subject ID (auto-generated if not provided)",
            min_length=1,
            max_length=64,
        ),
    ] = None,
    threads: Annotated[
        int, Form(description="Number of processing threads", ge=1, le=32)
    ] = 4,
    use_3T_atlas: Annotated[
        bool, Form(description="Use 3T atlas instead of 1.5T")
    ] = True,
    no_biasfield: Annotated[
        bool, Form(description="Skip bias field correction")
    ] = False,
    no_cereb: Annotated[
        bool, Form(description="Skip cerebellum sub-segmentation")
    ] = False,
    no_hypothal: Annotated[
        bool, Form(description="Skip hypothalamus segmentation")
    ] = False,
) -> JobCreateResponse:
    """
    Upload an MRI file and queue it for processing with FastSurfer.
    
    The processing is asynchronous - this endpoint returns immediately with a job ID.
    Use the /jobs/{job_id} endpoint to check the status of your job.
    
    **Processing Types:**
    - `seg_only`: Segmentation only (~5 minutes on GPU)
    - `surf_only`: Surface reconstruction only (~60-90 minutes, requires FreeSurfer license)
    - `full`: Full pipeline - segmentation + surface reconstruction
    
    **Input Requirements:**
    - File format: .nii, .nii.gz, or .mgz
    - Resolution: 0.7mm - 1mm isotropic recommended
    - Quality: 3T scanner images preferred
    - Max size: 500MB
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB",
        )
    
    # Sanitize and validate subject_id
    if subject_id:
        subject_id = sanitize_subject_id(subject_id)
        if not subject_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subject_id. Use only alphanumeric characters, hyphens, and underscores.",
            )
    
    # Generate unique filename for storage
    file_id = str(uuid.uuid4())[:8]
    safe_filename = f"{file_id}_{file.filename}"
    input_path = os.path.join(settings.DATA_INPUT_DIR, safe_filename)
    
    # Ensure input directory exists
    os.makedirs(settings.DATA_INPUT_DIR, exist_ok=True)
    
    # Save uploaded file
    try:
        async with aiofiles.open(input_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )
    
    # Create processing options
    options = ProcessingOptions(
        threads=threads,
        use_3T_atlas=use_3T_atlas,
        no_biasfield=no_biasfield,
        no_cereb=no_cereb,
        no_hypothal=no_hypothal,
    )
    
    # Create job
    job = job_manager.create_job(
        input_file=input_path,
        processing_type=processing_type,
        subject_id=subject_id,
        options=options,
    )
    
    return job


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List Jobs",
    description="List all processing jobs with pagination",
)
async def list_jobs(
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Items per page", ge=1, le=100)] = 10,
    status_filter: Annotated[
        JobStatus | None,
        Query(description="Filter by job status"),
    ] = None,
) -> JobListResponse:
    """
    List all MRI processing jobs.
    
    Results are sorted by creation time (newest first) and paginated.
    """
    return job_manager.list_jobs(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get Job Status",
    description="Get the status of a specific processing job",
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get the current status of a processing job.
    
    **Status Values:**
    - `queued`: Job is waiting to be processed
    - `processing`: Job is currently being processed
    - `completed`: Job finished successfully
    - `failed`: Job failed (check error_message)
    - `cancelled`: Job was cancelled
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    return job


@router.get(
    "/jobs/{job_id}/results",
    response_model=JobResultResponse,
    summary="Get Job Results",
    description="Get the results of a completed processing job",
    responses={
        404: {"model": ErrorResponse, "description": "Job not found or not completed"},
    },
)
async def get_job_results(job_id: str) -> JobResultResponse:
    """
    Get the results of a completed job including output files.
    
    Only available for jobs with status `completed`.
    """
    results = job_manager.get_job_results(job_id)
    
    if not results:
        # Check if job exists
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        elif job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} is not completed. Current status: {job.status.value}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Results for job {job_id} not found",
            )
    
    return results


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Job",
    description="Cancel a queued job",
    responses={
        400: {"model": ErrorResponse, "description": "Job cannot be cancelled"},
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def cancel_job(job_id: str) -> None:
    """
    Cancel a queued job.
    
    Only jobs with status `queued` can be cancelled.
    Jobs that are already processing, completed, or failed cannot be cancelled.
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    if job.status != JobStatus.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status.value}",
        )
    
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job",
        )
    
    return None


@router.get(
    "/jobs/{job_id}/report",
    summary="Download Volumetry Report",
    description="Download a PDF volumetry report for a completed job",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF volumetry report",
        },
        400: {"model": ErrorResponse, "description": "Job not completed"},
        404: {"model": ErrorResponse, "description": "Job not found or stats not available"},
    },
)
async def download_report(job_id: str) -> Response:
    """
    Download a PDF volumetry report for a completed processing job.
    
    The report includes:
    - Tissue segmentation volumes (WM, GM, CSF)
    - Macrostructures (Cerebrum, Cerebellum, Brainstem)
    - Subcortical structures (Hippocampus, Amygdala, Caudate, etc.)
    - Cortical regions by lobe
    
    All volumes are presented as absolute values (cm³) and relative to ICV (%).
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed. Current status: {job.status.value}",
        )
    
    # Find stats directory for this job using the subject_id
    subject_dir_name = job.subject_id if job.subject_id else f"subject_{job_id}"
    output_dir = Path(settings.DATA_OUTPUT_DIR) / subject_dir_name
    stats_dir = output_dir / "stats"
    
    if not stats_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stats directory not found for job {job_id}. Processing may not be complete.",
        )
    
    # Parse stats files
    try:
        parser = StatsParser(stats_dir)
        volumetry_data = parser.parse_all()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse stats files: {str(e)}",
        )
    
    # Extract report data
    extractor = VolumeExtractor(volumetry_data)
    report_data = extractor.extract_all(
        subject_id=job.subject_id or job_id,
        report_date=datetime.now().strftime("%d-%b-%Y"),
    )
    
    # Generate PDF
    try:
        generator = PDFGenerator()
        pdf_bytes = generator.generate(report_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}",
        )
    
    # Return PDF response
    filename = f"volumetry_report_{job.subject_id or job_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
