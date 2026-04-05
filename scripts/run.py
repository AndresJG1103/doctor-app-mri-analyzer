#!/usr/bin/env python3
"""Script to run the MRI Report API."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import uvicorn

from app.core.config import settings


def main() -> None:
    """Run the FastAPI application."""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"API docs available at: http://{settings.HOST}:{settings.PORT}{settings.API_V1_STR}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
