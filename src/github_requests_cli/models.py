"""Shared data models and protocols for repository health scans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Settings:
    github_api_key: str | None
    request_timeout_seconds: float


@dataclass(frozen=True)
class RepoHealth:
    full_name: str
    html_url: str
    archived: bool
    latest_commit_age: str
    latest_commit_date: datetime | None
    open_issue_count: int
    open_pr_count: int
    detected_language: str | None
    license_present: bool
    license_name: str | None
    readme_present: bool
    ci_workflow_present: bool


class GithubClient(Protocol):
    def get_repo(self, full_name_or_id: str): ...

    def search_issues(self, query: str): ...
