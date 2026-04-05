"""FastSurfer Service - Integration with FastSurfer Docker container."""

import logging
import os
import platform
from typing import Any

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from app.core.config import settings
from app.models.schemas import ProcessingOptions, ProcessingType

logger = logging.getLogger(__name__)


class FastSurferService:
    """Service for running FastSurfer processing via Docker."""

    def __init__(self) -> None:
        self._docker_client: docker.DockerClient | None = None

    @property
    def docker_client(self) -> docker.DockerClient:
        """Get Docker client, creating if necessary."""
        if self._docker_client is None:
            self._docker_client = docker.from_env()
        return self._docker_client

    def is_available(self) -> bool:
        """Check if FastSurfer Docker image is available."""
        try:
            self.docker_client.images.get(settings.FASTSURFER_IMAGE)
            return True
        except ImageNotFound:
            return False
        except Exception as e:
            logger.error(f"Error checking FastSurfer availability: {e}")
            return False

    def pull_image(self) -> bool:
        """Pull the FastSurfer Docker image."""
        try:
            logger.info(f"Pulling FastSurfer image: {settings.FASTSURFER_IMAGE}")
            self.docker_client.images.pull(settings.FASTSURFER_IMAGE)
            logger.info("FastSurfer image pulled successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to pull FastSurfer image: {e}")
            return False

    def _build_fastsurfer_command(
        self,
        input_file: str,
        subject_id: str,
        processing_type: ProcessingType,
        options: ProcessingOptions,
    ) -> list[str]:
        """Build the FastSurfer command with appropriate flags."""
        cmd = [
            "--t1", f"/data/input/{os.path.basename(input_file)}",
            "--sd", "/data/output",
            "--sid", subject_id,
            "--threads", str(options.threads),
            "--allow_root",  # Required when running in Docker without specific user
        ]

        # Processing type flags
        if processing_type == ProcessingType.SEG_ONLY:
            cmd.append("--seg_only")
        elif processing_type == ProcessingType.SURF_ONLY:
            cmd.append("--surf_only")
            cmd.extend(["--fs_license", "/data/licenses/license.txt"])
        else:  # FULL
            cmd.extend(["--fs_license", "/data/licenses/license.txt"])

        # Optional flags
        if options.use_3T_atlas:
            cmd.append("--3T")
        
        if options.no_biasfield:
            cmd.append("--no_biasfield")
        
        if options.no_cereb:
            cmd.append("--no_cereb")
        
        if options.no_hypothal:
            cmd.append("--no_hypothal")
        
        if options.vox_size != "min":
            cmd.extend(["--vox_size", options.vox_size])

        # Device configuration
        if settings.FASTSURFER_USE_GPU:
            cmd.extend(["--device", settings.FASTSURFER_DEVICE])
        else:
            cmd.extend(["--device", "cpu"])

        return cmd

    def _get_volume_mounts(self) -> dict[str, dict[str, str]]:
        """Get Docker volume mount configuration."""
        # When running inside Docker, use the mounted /data paths directly
        # When running on host, convert to local paths
        
        # Check if we're running inside Docker
        is_in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER")
        
        logger.info(f"Is running in Docker: {is_in_docker}")
        
        if is_in_docker:
            # Inside Docker - we need HOST paths for Docker-in-Docker
            # HOST_DATA_PATH must be set to the Windows path
            # Docker Desktop for Windows uses /host_mnt/e/ or //e/ format internally
            host_data_base = os.environ.get("HOST_DATA_PATH", "")
            
            if not host_data_base:
                logger.error("HOST_DATA_PATH environment variable not set!")
                logger.error("Set it in .env to your data folder absolute path")
                logger.error("Example Windows: E:/codes/Personal/mri_report/data")
                raise ValueError("HOST_DATA_PATH must be set for Docker-in-Docker")
            
            logger.info(f"Using HOST_DATA_PATH: {host_data_base}")
            
            volumes = {
                f"{host_data_base}/input": {"bind": "/data/input", "mode": "ro"},
                f"{host_data_base}/output": {"bind": "/data/output", "mode": "rw"},
                f"{host_data_base}/licenses": {"bind": "/data/licenses", "mode": "ro"},
            }
            
            logger.info(f"Volume mounts for FastSurfer: {volumes}")
            return volumes
        else:
            # Running on host directly - use local paths
            base_dir = os.getcwd()
            
            host_input = os.path.join(base_dir, "data", "input")
            host_output = os.path.join(base_dir, "data", "output")
            host_licenses = os.path.join(base_dir, "data", "licenses")
            
            return {
                host_input: {"bind": "/data/input", "mode": "ro"},
                host_output: {"bind": "/data/output", "mode": "rw"},
                host_licenses: {"bind": "/data/licenses", "mode": "ro"},
            }

    def process_mri(
        self,
        input_file: str,
        subject_id: str,
        processing_type: ProcessingType,
        options: ProcessingOptions,
        progress_callback: callable = None,
    ) -> dict[str, Any]:
        """
        Process an MRI file using FastSurfer.
        
        Args:
            input_file: Path to the input MRI file
            subject_id: Subject identifier for output
            processing_type: Type of processing to perform
            options: Processing options
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting FastSurfer processing for {subject_id}")
        logger.info(f"Processing type: {processing_type.value}")
        logger.info(f"Input file: {input_file}")

        # Verify input file exists
        input_path = os.path.join(settings.DATA_INPUT_DIR, os.path.basename(input_file))
        if not os.path.exists(input_path.replace("/data", "./data")):
            # Try with the provided path directly
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Input file not found: {input_file}")

        # Build command
        cmd = self._build_fastsurfer_command(
            input_file, subject_id, processing_type, options
        )
        logger.info(f"FastSurfer command: {' '.join(cmd)}")

        # Get volume mounts
        volumes = self._get_volume_mounts()
        logger.info(f"Volume mounts: {volumes}")

        # Configure GPU if enabled
        device_requests = []
        if settings.FASTSURFER_USE_GPU:
            device_requests = [
                docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])
            ]

        try:
            # Ensure image is available
            if not self.is_available():
                logger.info("FastSurfer image not found, pulling...")
                self.pull_image()

            # Get user ID for proper file permissions
            # On Windows/Docker, use root or specific UID
            if platform.system() == "Windows":
                user = None  # Let Docker handle it
            else:
                try:
                    uid = os.getuid()
                    gid = os.getgid()
                    user = f"{uid}:{gid}"
                except AttributeError:
                    # Windows doesn't have getuid
                    user = None

            # Run container with better error capture
            logger.info(f"Running FastSurfer container (user={user})")
            logger.info(f"Command: {' '.join(cmd)}")
            
            # Use detach=True to get container object and capture logs properly
            container = self.docker_client.containers.run(
                image=settings.FASTSURFER_IMAGE,
                command=cmd,
                volumes=volumes,
                device_requests=device_requests if device_requests else None,
                user=user,
                remove=False,  # Don't auto-remove so we can get logs
                detach=True,
            )
            
            # Wait for container to finish
            result = container.wait()
            exit_code = result.get("StatusCode", -1)
            
            # Get logs
            stdout_logs = container.logs(stdout=True, stderr=False).decode("utf-8")
            stderr_logs = container.logs(stdout=False, stderr=True).decode("utf-8")
            
            # Clean up container
            container.remove()
            
            if exit_code != 0:
                error_msg = f"FastSurfer exited with code {exit_code}"
                if stderr_logs:
                    error_msg += f"\nStderr: {stderr_logs[-2000:]}"  # Last 2000 chars
                if stdout_logs:
                    error_msg += f"\nStdout: {stdout_logs[-1000:]}"  # Last 1000 chars
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "exit_code": exit_code,
                    "stdout": stdout_logs,
                    "stderr": stderr_logs,
                }

            logger.info("FastSurfer completed successfully")
            if stdout_logs:
                logger.debug(f"Output: {stdout_logs[:1000]}...")

            # Calculate output path
            output_path = os.path.join(settings.DATA_OUTPUT_DIR, subject_id)

            return {
                "success": True,
                "output_path": output_path,
                "message": "Processing completed successfully",
                "logs": stdout_logs,
            }

        except ContainerError as e:
            error_msg = f"FastSurfer container error: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "exit_code": e.exit_status,
            }
        except ImageNotFound as e:
            error_msg = f"FastSurfer image not found: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }
        except Exception as e:
            error_msg = f"FastSurfer processing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
            }

    def get_image_info(self) -> dict[str, Any]:
        """Get information about the FastSurfer Docker image."""
        try:
            image = self.docker_client.images.get(settings.FASTSURFER_IMAGE)
            return {
                "id": image.short_id,
                "tags": image.tags,
                "created": image.attrs.get("Created"),
                "size": image.attrs.get("Size"),
            }
        except ImageNotFound:
            return {"error": "Image not found"}
        except Exception as e:
            return {"error": str(e)}

    def health_check(self) -> dict[str, Any]:
        """Check FastSurfer service health."""
        try:
            # Check Docker connectivity
            self.docker_client.ping()
            
            # Check if image is available
            image_available = self.is_available()
            
            return {
                "status": "healthy" if image_available else "degraded",
                "docker": "connected",
                "image_available": image_available,
                "image": settings.FASTSURFER_IMAGE,
                "gpu_enabled": settings.FASTSURFER_USE_GPU,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Global FastSurfer service instance
fastsurfer_service = FastSurferService()
