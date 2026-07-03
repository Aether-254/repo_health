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
class RepositoryDocument:
    name: str
    path: str
    markdown: str


@dataclass(frozen=True)
class DescriptorSummary:
    path: str
    kind: str
    summary: tuple[str, ...]


@dataclass(frozen=True)
class RepoHealth:
    full_name: str
    html_url: str
    archived: bool
    status: str
    default_branch: str
    latest_commit_age: str
    latest_commit_date: datetime | None
    open_issue_count: int
    open_pr_count: int
    detected_language: str | None
    license_present: bool
    license_name: str | None
    license_key: str | None
    readme_present: bool
    ci_workflow_present: bool
    documents: tuple[RepositoryDocument, ...] = ()
    descriptors: tuple[DescriptorSummary, ...] = ()


class GithubClient(Protocol):
    def get_repo(self, full_name_or_id: str): ...

    def search_issues(self, query: str): ...
