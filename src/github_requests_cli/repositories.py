"""Repository argument parsing."""

from __future__ import annotations

import re

REPOSITORY_RE = re.compile(
    r"^(?:https?://github\.com/)?(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def normalize_repository(value: str) -> str:
    match = REPOSITORY_RE.match(value.strip())
    if not match:
        raise ValueError("Repository must be in owner/name form or a github.com repository URL.")
    return f"{match.group('owner')}/{match.group('repo')}"
