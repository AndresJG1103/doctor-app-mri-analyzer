"""Job Manager - Handles job creation, status tracking, and queue management."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from redis import Redis

from app.core.config import settings
from app.core.redis import get_redis
from app.models.schemas import (
    JobCreateResponse,
    JobListResponse,
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
    ProcessingOptions,
    ProcessingType,
)

logger = logging.getLogger(__name__)

# Redis key prefixes
JOB_KEY_PREFIX = "mri:job:"
JOB_QUEUE_KEY = "mri:queue"
JOB_INDEX_KEY = "mri:jobs"


class JobManager:
    """Manages MRI processing jobs with Redis backend."""

    def __init__(self, redis_client: Redis | None = None) -> None:
        self._redis = redis_client

    @property
    def redis(self) -> Redis:
        """Get Redis client."""
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    def _job_key(self, job_id: str) -> str:
        """Generate Redis key for a job."""
        return f"{JOB_KEY_PREFIX}{job_id}"

    def _serialize_job(self, job_data: dict[str, Any]) -> str:
        """Serialize job data to JSON string."""
        serialized = {}
        for key, value in job_data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, (ProcessingType, JobStatus)):
                serialized[key] = value.value
            elif isinstance(value, ProcessingOptions):
                serialized[key] = value.model_dump()
            else:
                serialized[key] = value
        return json.dumps(serialized)

    def _deserialize_job(self, job_json: str) -> dict[str, Any]:
        """Deserialize job data from JSON string."""
        data = json.loads(job_json)
        
        # Convert datetime strings back to datetime objects
        for field in ["created_at", "started_at", "completed_at"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert enum strings back to enums
        if data.get("status"):
            data["status"] = JobStatus(data["status"])
        if data.get("processing_type"):
            data["processing_type"] = ProcessingType(data["processing_type"])
        
        return data

    def create_job(
        self,
        input_file: str,
        processing_type: ProcessingType,
        subject_id: str | None = None,
        options: ProcessingOptions | None = None,
    ) -> JobCreateResponse:
        """Create a new processing job."""
        job_id = str(uuid.uuid4())
        
        # Generate subject_id if not provided
        if not subject_id:
            subject_id = f"subject_{job_id[:8]}"
        
        # Default options
        if options is None:
            options = ProcessingOptions()
        
        now = datetime.utcnow()
        
        job_data = {
            "job_id": job_id,
            "status": JobStatus.QUEUED,
            "subject_id": subject_id,
            "processing_type": processing_type,
            "input_file": input_file,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "progress": 0,
            "error_message": None,
            "output_path": None,
            "options": options,
        }
        
        # Store job in Redis
        self.redis.set(self._job_key(job_id), self._serialize_job(job_data))
        
        # Add to job index
        self.redis.zadd(JOB_INDEX_KEY, {job_id: now.timestamp()})
        
        # Add to processing queue
        self.redis.rpush(JOB_QUEUE_KEY, job_id)
        
        logger.info(f"Created job {job_id} for subject {subject_id}")
        
        return JobCreateResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            subject_id=subject_id,
            processing_type=processing_type,
            created_at=now,
            message="Job enqueued successfully",
        )

    def get_job(self, job_id: str) -> JobStatusResponse | None:
        """Get job status by ID."""
        job_json = self.redis.get(self._job_key(job_id))
        
        if not job_json:
            return None
        
        job_data = self._deserialize_job(job_json)
        
        # Remove options from response (not needed for status)
        job_data.pop("options", None)
        
        return JobStatusResponse(**job_data)

    def get_job_with_options(self, job_id: str) -> dict[str, Any] | None:
        """Get full job data including options."""
        job_json = self.redis.get(self._job_key(job_id))
        
        if not job_json:
            return None
        
        return self._deserialize_job(job_json)

    def update_job(self, job_id: str, **updates: Any) -> bool:
        """Update job fields."""
        job_json = self.redis.get(self._job_key(job_id))
        
        if not job_json:
            return False
        
        job_data = self._deserialize_job(job_json)
        job_data.update(updates)
        
        self.redis.set(self._job_key(job_id), self._serialize_job(job_data))
        
        logger.info(f"Updated job {job_id}: {updates}")
        return True

    def start_job(self, job_id: str) -> bool:
        """Mark a job as started."""
        return self.update_job(
            job_id,
            status=JobStatus.PROCESSING,
            started_at=datetime.utcnow(),
        )

    def complete_job(self, job_id: str, output_path: str) -> bool:
        """Mark a job as completed."""
        return self.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            progress=100,
            output_path=output_path,
        )

    def fail_job(self, job_id: str, error_message: str) -> bool:
        """Mark a job as failed."""
        return self.update_job(
            job_id,
            status=JobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message=error_message,
        )

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job."""
        job = self.get_job(job_id)
        
        if not job:
            return False
        
        if job.status != JobStatus.QUEUED:
            return False
        
        # Remove from queue
        self.redis.lrem(JOB_QUEUE_KEY, 0, job_id)
        
        # Update status
        return self.update_job(
            job_id,
            status=JobStatus.CANCELLED,
            completed_at=datetime.utcnow(),
        )

    def update_progress(self, job_id: str, progress: int) -> bool:
        """Update job progress percentage."""
        return self.update_job(job_id, progress=min(max(progress, 0), 100))

    def list_jobs(
        self,
        page: int = 1,
        page_size: int = 10,
        status_filter: JobStatus | None = None,
    ) -> JobListResponse:
        """List jobs with pagination."""
        # Get all job IDs sorted by creation time (newest first)
        start = (page - 1) * page_size
        end = start + page_size - 1
        
        job_ids = self.redis.zrevrange(JOB_INDEX_KEY, start, end)
        total = self.redis.zcard(JOB_INDEX_KEY)
        
        jobs = []
        for job_id in job_ids:
            job = self.get_job(job_id)
            if job:
                if status_filter is None or job.status == status_filter:
                    jobs.append(job)
        
        return JobListResponse(
            jobs=jobs,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_next_queued_job(self) -> str | None:
        """Get the next job from the queue."""
        return self.redis.lpop(JOB_QUEUE_KEY)

    def get_queue_length(self) -> int:
        """Get the number of jobs in the queue."""
        return self.redis.llen(JOB_QUEUE_KEY)

    def get_job_results(self, job_id: str) -> JobResultResponse | None:
        """Get job results including output files."""
        import os
        
        job = self.get_job(job_id)
        
        if not job or job.status != JobStatus.COMPLETED:
            return None
        
        if not job.output_path:
            return None
        
        # List files in output directory
        files = []
        if os.path.exists(job.output_path):
            for root, _, filenames in os.walk(job.output_path):
                for filename in filenames:
                    rel_path = os.path.relpath(
                        os.path.join(root, filename), job.output_path
                    )
                    files.append(rel_path)
        
        # Try to load statistics if available
        statistics = None
        stats_file = os.path.join(job.output_path, "stats", "aseg.stats")
        if os.path.exists(stats_file):
            # Parse basic stats (simplified)
            statistics = {"stats_file": stats_file}
        
        return JobResultResponse(
            job_id=job_id,
            status=job.status,
            subject_id=job.subject_id,
            output_path=job.output_path,
            files=files,
            statistics=statistics,
        )


# Global job manager instance
job_manager = JobManager()
