"""Repository activity status helpers."""

from __future__ import annotations

from datetime import UTC, datetime


def repository_status(
    *, archived: bool, latest_commit_date: datetime | None, now: datetime | None = None
) -> str:
    if archived:
        return "Archived"
    if latest_commit_date is None:
        return "Inactive"

    now = now or datetime.now(UTC)
    days = max((now - latest_commit_date).days, 0)
    if days <= 60:
        return "Active"
    if days <= 120:
        return "Semi-active"
    if days < 365:
        return "Low activity"
    return "Inactive"
