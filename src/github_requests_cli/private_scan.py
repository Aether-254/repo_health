"""PyGithub-backed scans for private repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from github_requests_cli.models import GithubClient, RepoHealth
from github_requests_cli.time_utils import human_age


def github_client(token: str | None) -> GithubClient:
    if not token:
        raise ValueError("Private repository scans require GITHUB_API_KEY in .env or --token.")
    try:
        from github import Github  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError(
            "Private repository scans require PyGithub. Install with `pip install -e .[private]`."
        ) from exc
    return cast(GithubClient, Github(token))


def total_search_count(client: GithubClient, query: str) -> int:
    return int(client.search_issues(query).totalCount)


def latest_commit_datetime(repo) -> datetime | None:
    commits = repo.get_commits()
    if commits.totalCount == 0:
        return None

    value = commits[0].commit.author.date
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def has_readme(repo) -> bool:
    try:
        repo.get_readme()
    except Exception as exc:
        if not is_github_not_found(exc):
            raise
        return False
    return True


def has_ci_workflow(repo) -> bool:
    try:
        workflows = repo.get_contents(".github/workflows")
    except Exception as exc:
        if not is_github_not_found(exc):
            raise
        return False

    if not isinstance(workflows, list):
        workflows = [workflows]

    return any(item.type == "file" and item.name.endswith((".yml", ".yaml")) for item in workflows)


def license_info(repo) -> tuple[bool, str | None]:
    try:
        license_file = repo.get_license()
    except Exception as exc:
        if not is_github_not_found(exc):
            raise
        return False, None

    license_name = None
    if getattr(license_file, "license", None):
        license_name = getattr(license_file.license, "name", None)

    return True, license_name


def is_github_not_found(exc: Exception) -> bool:
    status = getattr(exc, "status", None)
    if status == 404:
        return True
    return exc.__class__.__name__ == "UnknownObjectException"


def scan_repository(client: GithubClient, repository: str) -> RepoHealth:
    repo = client.get_repo(repository)
    latest_commit_date = latest_commit_datetime(repo)
    license_present, license_name = license_info(repo)

    return RepoHealth(
        full_name=repo.full_name,
        html_url=repo.html_url,
        archived=bool(repo.archived),
        latest_commit_age=human_age(latest_commit_date),
        latest_commit_date=latest_commit_date,
        open_issue_count=total_search_count(client, f"repo:{repo.full_name} is:issue is:open"),
        open_pr_count=total_search_count(client, f"repo:{repo.full_name} is:pr is:open"),
        detected_language=repo.language,
        license_present=license_present,
        license_name=license_name,
        readme_present=has_readme(repo),
        ci_workflow_present=has_ci_workflow(repo),
    )
