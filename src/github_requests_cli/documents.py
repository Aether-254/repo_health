"""Repository document discovery."""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any

from github_requests_cli.models import RepositoryDocument

DOCUMENT_CANDIDATES = {
    "README": ("README.md", "README.rst", "README.txt"),
    "Code of Conduct": (
        "CODE_OF_CONDUCT.md",
        ".github/CODE_OF_CONDUCT.md",
        "docs/CODE_OF_CONDUCT.md",
    ),
    "Contributing": (
        "CONTRIBUTING.md",
        ".github/CONTRIBUTING.md",
        "docs/CONTRIBUTING.md",
    ),
    "License": ("LICENSE", "LICENSE.md", "COPYING"),
    "Security": ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"),
}


def decode_content_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    content = payload.get("content")
    if not isinstance(content, str):
        return None
    if payload.get("encoding") != "base64":
        return content
    normalized = content.replace("\n", "")
    return base64.b64decode(normalized).decode("utf-8", errors="replace")


def collect_documents(fetch_content: Callable[[str], Any | None]) -> tuple[RepositoryDocument, ...]:
    documents: list[RepositoryDocument] = []
    for document_name, paths in DOCUMENT_CANDIDATES.items():
        for path in paths:
            payload = fetch_content(path)
            markdown = decode_content_payload(payload)
            if markdown is None:
                continue
            documents.append(RepositoryDocument(document_name, path, markdown))
            break
    return tuple(documents)
