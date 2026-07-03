"""Datetime parsing and presentation helpers."""

from __future__ import annotations

from datetime import UTC, datetime


def human_age(since: datetime | None, *, now: datetime | None = None) -> str:
    if since is None:
        return "No commits found"

    now = now or datetime.now(UTC)
    delta = now - since
    days = max(delta.days, 0)

    if days == 0:
        hours = max(delta.seconds // 3600, 0)
        if hours == 0:
            return "Less than 1 hour"
        if hours == 1:
            return "1 hour"
        return f"{hours} hours"

    if days == 1:
        return "1 day"
    if days < 30:
        return f"{days} days"
    if days < 365:
        months = days // 30
        return "1 month" if months == 1 else f"{months} months"

    years = days // 365
    return "1 year" if years == 1 else f"{years} years"


def parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
