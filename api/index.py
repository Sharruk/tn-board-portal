"""
Vercel Serverless Function Entry Point for FastAPI Backend.

This file is detected by Vercel's Python runtime and exposes the FastAPI
`app` instance for serverless request execution.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path so app modules (app.main, app.config, etc.) resolve
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
