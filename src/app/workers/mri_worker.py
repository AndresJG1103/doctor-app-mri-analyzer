"""MRI Worker - Background worker for processing MRI jobs."""

import logging
import signal
import sys
import time
from typing import Any

from app.core.config import settings
from app.core.redis import redis_client
from app.models.schemas import ProcessingOptions, ProcessingType
from app.services.fastsurfer import fastsurfer_service
from app.services.job_manager import job_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MRIWorker:
    """Worker that processes MRI jobs from the queue."""

    def __init__(self) -> None:
        self.running = False
        self.current_job_id: str | None = None

    def start(self) -> None:
        """Start the worker loop."""
        logger.info("Starting MRI Worker...")
        logger.info(f"FastSurfer image: {settings.FASTSURFER_IMAGE}")
        logger.info(f"GPU enabled: {settings.FASTSURFER_USE_GPU}")
        
        # Connect to Redis
        redis_client.connect()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        
        # Check FastSurfer availability
        health = fastsurfer_service.health_check()
        logger.info(f"FastSurfer health: {health}")
        
        if health.get("status") == "unhealthy":
            logger.warning("FastSurfer service is unhealthy, worker may fail to process jobs")
        
        # Main loop
        logger.info("Worker ready, waiting for jobs...")
        self._process_loop()

    def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info("Stopping MRI Worker...")
        self.running = False
        
        # If processing a job, mark it as failed
        if self.current_job_id:
            logger.warning(f"Worker stopped while processing job {self.current_job_id}")
            job_manager.fail_job(
                self.current_job_id,
                "Worker stopped during processing",
            )
        
        redis_client.disconnect()
        logger.info("Worker stopped")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)

    def _process_loop(self) -> None:
        """Main processing loop."""
        while self.running:
            try:
                # Get next job from queue (blocking with timeout)
                job_id = job_manager.get_next_queued_job()
                
                if job_id:
                    self._process_job(job_id)
                else:
                    # No job available, wait before checking again
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in process loop: {e}", exc_info=True)
                time.sleep(5)  # Wait before retrying

    def _process_job(self, job_id: str) -> None:
        """Process a single job."""
        logger.info(f"Processing job: {job_id}")
        self.current_job_id = job_id
        
        try:
            # Get job details
            job_data = job_manager.get_job_with_options(job_id)
            
            if not job_data:
                logger.error(f"Job {job_id} not found")
                return
            
            # Mark job as started
            job_manager.start_job(job_id)
            
            # Extract job parameters
            input_file = job_data["input_file"]
            subject_id = job_data["subject_id"]
            processing_type = job_data["processing_type"]
            
            # Get options
            options_data = job_data.get("options", {})
            if isinstance(options_data, dict):
                options = ProcessingOptions(**options_data)
            else:
                options = options_data
            
            logger.info(f"Job {job_id}: Processing {input_file} as {subject_id}")
            logger.info(f"Job {job_id}: Type = {processing_type.value}")
            
            # Update progress
            job_manager.update_progress(job_id, 10)
            
            # Run FastSurfer processing
            result = fastsurfer_service.process_mri(
                input_file=input_file,
                subject_id=subject_id,
                processing_type=processing_type,
                options=options,
                progress_callback=lambda p: job_manager.update_progress(job_id, p),
            )
            
            # Handle result
            if result.get("success"):
                job_manager.complete_job(job_id, result["output_path"])
                logger.info(f"Job {job_id} completed successfully")
            else:
                error_msg = result.get("error", "Unknown error")
                job_manager.fail_job(job_id, error_msg)
                logger.error(f"Job {job_id} failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            job_manager.fail_job(job_id, str(e))
        finally:
            self.current_job_id = None

    def get_status(self) -> dict[str, Any]:
        """Get worker status."""
        return {
            "running": self.running,
            "current_job": self.current_job_id,
            "queue_length": job_manager.get_queue_length(),
            "redis_connected": redis_client.is_connected(),
            "fastsurfer_health": fastsurfer_service.health_check(),
        }


def main() -> None:
    """Main entry point for the worker."""
    worker = MRIWorker()
    
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
    finally:
        worker.stop()


if __name__ == "__main__":
    main()
