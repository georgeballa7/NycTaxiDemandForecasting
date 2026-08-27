import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
)

API_TIMEOUT = int(
    os.getenv("API_TIMEOUT", "60")
)
