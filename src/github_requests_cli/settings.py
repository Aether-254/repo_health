"""Environment-backed CLI settings."""

from __future__ import annotations

import os
from pathlib import Path

from github_requests_cli.models import Settings


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_settings() -> Settings:
    load_dotenv()

    timeout = os.getenv("REQUEST_TIMEOUT_SECONDS", "20")
    try:
        request_timeout_seconds = float(timeout)
    except ValueError:
        request_timeout_seconds = 20.0

    return Settings(
        github_api_key=os.getenv("GITHUB_API_KEY") or os.getenv("GITHUB_TOKEN"),
        request_timeout_seconds=request_timeout_seconds,
    )
