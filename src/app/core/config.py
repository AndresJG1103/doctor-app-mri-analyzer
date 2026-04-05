"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # API Configuration
    # -------------------------------------------------------------------------
    PROJECT_NAME: str = "MRI Report API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "FastAPI service for MRI processing using FastSurfer"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # -------------------------------------------------------------------------
    # CORS Configuration
    # -------------------------------------------------------------------------
    ALLOWED_ORIGINS: list[str] = ["*"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        return v

    # -------------------------------------------------------------------------
    # FastSurfer Configuration
    # -------------------------------------------------------------------------
    FASTSURFER_IMAGE: str = "deepmi/fastsurfer:latest"
    FASTSURFER_USE_GPU: bool = False
    FASTSURFER_DEVICE: str = "cpu"  # cpu, cuda, cuda:0, cuda:1, etc.
    FASTSURFER_THREADS: int = 4

    # -------------------------------------------------------------------------
    # Data Paths
    # -------------------------------------------------------------------------
    DATA_INPUT_DIR: str = "/data/input"
    DATA_OUTPUT_DIR: str = "/data/output"
    FREESURFER_LICENSE_PATH: str = "/data/licenses/license.txt"

    # -------------------------------------------------------------------------
    # Redis Configuration
    # -------------------------------------------------------------------------
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # -------------------------------------------------------------------------
    # File Upload Configuration
    # -------------------------------------------------------------------------
    MAX_UPLOAD_SIZE: int = 524288000  # 500MB
    ALLOWED_EXTENSIONS: set[str] = {".nii", ".nii.gz", ".mgz"}

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_extensions(cls, v: str | set[str]) -> set[str]:
        """Parse allowed extensions from comma-separated string or set."""
        if isinstance(v, str):
            return {ext.strip() for ext in v.split(",")}
        return v

    # -------------------------------------------------------------------------
    # Worker Configuration
    # -------------------------------------------------------------------------
    MAX_CONCURRENT_JOBS: int = 2
    JOB_TIMEOUT: int = 7200  # 2 hours

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    AUTH_USERNAME: str = "admin"
    AUTH_PASSWORD: str = "changeme"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
