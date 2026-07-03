"""REST-backed scans for public repositories."""

from __future__ import annotations

import requests

from github_requests_cli.errors import GitHubApiError
from github_requests_cli.github_api import (
    api_get_json,
    api_get_optional_json,
    github_headers,
    raise_for_github_status,
    response_json,
)
from github_requests_cli.models import RepoHealth
from github_requests_cli.time_utils import human_age, parse_github_datetime


def public_search_count(session: requests.Session, query: str, *, timeout: float) -> int:
    params: dict[str, str | int] = {"q": query, "per_page": 1}
    response = session.get(
        "https://api.github.com/search/issues",
        params=params,
        timeout=timeout,
    )
    raise_for_github_status(response)
    try:
        return int(response_json(response)["total_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GitHubApiError("GitHub API response did not include a valid search count.") from exc


def public_readme_present(session: requests.Session, repository: str, *, timeout: float) -> bool:
    payload = api_get_optional_json(
        session,
        f"https://api.github.com/repos/{repository}/readme",
        timeout=timeout,
    )
    return payload is not None


def public_ci_workflow_present(
    session: requests.Session, repository: str, *, timeout: float
) -> bool:
    payload = api_get_optional_json(
        session,
        f"https://api.github.com/repos/{repository}/contents/.github/workflows",
        timeout=timeout,
    )
    if payload is None:
        return False
    if isinstance(payload, dict):
        payload = [payload]
    return any(
        item.get("type") == "file" and item.get("name", "").endswith((".yml", ".yaml"))
        for item in payload
    )


def public_license_info(
    session: requests.Session, repository: str, *, timeout: float
) -> tuple[bool, str | None]:
    payload = api_get_optional_json(
        session,
        f"https://api.github.com/repos/{repository}/license",
        timeout=timeout,
    )
    if payload is None:
        return False, None

    license_payload = payload.get("license") or {}
    return True, license_payload.get("name")


def scan_public_repository(
    repository: str, *, timeout: float, token: str | None = None
) -> RepoHealth:
    with requests.Session() as session:
        session.headers.update(github_headers(token))
        repo = api_get_json(
            session,
            f"https://api.github.com/repos/{repository}",
            timeout=timeout,
        )
        commits = api_get_optional_json(
            session,
            f"https://api.github.com/repos/{repository}/commits?per_page=1",
            timeout=timeout,
        )
        latest_commit_date = None
        if commits:
            latest_commit_date = parse_github_datetime(
                commits[0].get("commit", {}).get("committer", {}).get("date")
            )

        license_present, license_name = public_license_info(session, repository, timeout=timeout)

        try:
            return RepoHealth(
                full_name=repo["full_name"],
                html_url=repo["html_url"],
                archived=bool(repo["archived"]),
                latest_commit_age=human_age(latest_commit_date),
                latest_commit_date=latest_commit_date,
                open_issue_count=public_search_count(
                    session, f"repo:{repo['full_name']} is:issue is:open", timeout=timeout
                ),
                open_pr_count=public_search_count(
                    session, f"repo:{repo['full_name']} is:pr is:open", timeout=timeout
                ),
                detected_language=repo.get("language"),
                license_present=license_present,
                license_name=license_name,
                readme_present=public_readme_present(session, repository, timeout=timeout),
                ci_workflow_present=public_ci_workflow_present(
                    session, repository, timeout=timeout
                ),
            )
        except (KeyError, TypeError) as exc:
            raise GitHubApiError(
                "GitHub API response did not include expected repository fields."
            ) from exc
