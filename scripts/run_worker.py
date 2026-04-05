#!/usr/bin/env python3
"""Script to run the MRI processing worker."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from app.workers.mri_worker import main

if __name__ == "__main__":
    main()
