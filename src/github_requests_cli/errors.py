"""User-facing GitHub API errors."""

from __future__ import annotations


class PublicRepositoryNotFoundError(RuntimeError):
    """Public REST API cannot read the repository."""


class GitHubApiError(RuntimeError):
    """GitHub REST API returned a known user-facing failure."""
