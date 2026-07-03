"""PyGithub-backed scans for private repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from github_requests_cli.descriptors import collect_descriptor_summaries
from github_requests_cli.documents import collect_documents
from github_requests_cli.license_utils import short_license_name
from github_requests_cli.models import GithubClient, RepoHealth
from github_requests_cli.status import repository_status
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


def license_info(repo) -> tuple[bool, str | None, str | None]:
    try:
        license_file = repo.get_license()
    except Exception as exc:
        if not is_github_not_found(exc):
            raise
        return False, None, None

    license_name = None
    license_key = None
    if getattr(license_file, "license", None):
        license_name = getattr(license_file.license, "name", None)
        license_key = short_license_name(
            license_name, getattr(license_file.license, "spdx_id", None)
        )

    return True, license_name, license_key


def is_github_not_found(exc: Exception) -> bool:
    status = getattr(exc, "status", None)
    if status == 404:
        return True
    return exc.__class__.__name__ == "UnknownObjectException"


def scan_repository(client: GithubClient, repository: str) -> RepoHealth:
    repo = client.get_repo(repository)
    latest_commit_date = latest_commit_datetime(repo)
    license_present, license_name, license_key = license_info(repo)
    default_branch = str(getattr(repo, "default_branch", None) or "HEAD")

    def fetch_content(path: str):
        return _private_content(repo, path, ref=default_branch)

    documents = collect_documents(fetch_content)
    root_contents = _private_root_contents(repo, ref=default_branch)
    descriptors = collect_descriptor_summaries(root_contents, fetch_content)

    return RepoHealth(
        full_name=repo.full_name,
        html_url=repo.html_url,
        archived=bool(repo.archived),
        status=repository_status(
            archived=bool(repo.archived),
            latest_commit_date=latest_commit_date,
        ),
        default_branch=default_branch,
        latest_commit_age=human_age(latest_commit_date),
        latest_commit_date=latest_commit_date,
        open_issue_count=total_search_count(client, f"repo:{repo.full_name} is:issue is:open"),
        open_pr_count=total_search_count(client, f"repo:{repo.full_name} is:pr is:open"),
        detected_language=repo.language,
        license_present=license_present,
        license_name=license_name,
        license_key=license_key,
        readme_present=any(document.name == "README" for document in documents),
        ci_workflow_present=has_ci_workflow(repo),
        documents=documents,
        descriptors=descriptors,
    )


def _private_content(repo, path: str, *, ref: str):
    try:
        item = repo.get_contents(path, ref=ref)
    except Exception as exc:
        if not is_github_not_found(exc):
            raise
        return None
    if isinstance(item, list):
        return None
    return {
        "content": getattr(item, "content", None),
        "encoding": getattr(item, "encoding", "base64"),
        "path": getattr(item, "path", path),
    }


def _private_root_contents(repo, *, ref: str) -> list[dict]:
    try:
        items = repo.get_contents("", ref=ref)
    except Exception as exc:
        if not is_github_not_found(exc):
            raise
        return []
    if not isinstance(items, list):
        return []
    return [
        {
            "name": getattr(item, "name", ""),
            "path": getattr(item, "path", ""),
            "type": getattr(item, "type", ""),
        }
        for item in items
    ]
