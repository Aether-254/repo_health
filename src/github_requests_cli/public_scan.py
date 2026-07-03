"""REST-backed scans for public repositories."""

from __future__ import annotations

import requests

from github_requests_cli.descriptors import collect_descriptor_summaries
from github_requests_cli.documents import collect_documents
from github_requests_cli.errors import GitHubApiError
from github_requests_cli.github_api import (
    api_get_json,
    api_get_optional_json,
    github_headers,
    raise_for_github_status,
    response_json,
)
from github_requests_cli.license_utils import short_license_name
from github_requests_cli.models import RepoHealth
from github_requests_cli.status import repository_status
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


def public_content(
    session: requests.Session, repository: str, path: str, *, ref: str, timeout: float
):
    payload = api_get_optional_json(
        session,
        f"https://api.github.com/repos/{repository}/contents/{path}?ref={ref}",
        timeout=timeout,
    )
    if isinstance(payload, list):
        return None
    return payload


def public_readme_present(
    session: requests.Session, repository: str, *, ref: str, timeout: float
) -> bool:
    payload = public_content(session, repository, "README.md", ref=ref, timeout=timeout)
    return payload is not None


def public_ci_workflow_present(
    session: requests.Session, repository: str, *, ref: str, timeout: float
) -> bool:
    payload = api_get_optional_json(
        session,
        f"https://api.github.com/repos/{repository}/contents/.github/workflows?ref={ref}",
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
    session: requests.Session, repository: str, *, ref: str, timeout: float
) -> tuple[bool, str | None, str | None]:
    payload = api_get_optional_json(
        session,
        f"https://api.github.com/repos/{repository}/license?ref={ref}",
        timeout=timeout,
    )
    if payload is None:
        return False, None, None

    license_payload = payload.get("license") or {}
    license_name = license_payload.get("name")
    license_key = short_license_name(license_name, license_payload.get("spdx_id"))
    return True, license_name, license_key


def public_root_contents(
    session: requests.Session, repository: str, *, ref: str, timeout: float
) -> list[dict]:
    payload = api_get_optional_json(
        session,
        f"https://api.github.com/repos/{repository}/contents?ref={ref}",
        timeout=timeout,
    )
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


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
        try:
            full_name = repo["full_name"]
            html_url = repo["html_url"]
            archived = bool(repo["archived"])
        except (KeyError, TypeError) as exc:
            raise GitHubApiError(
                "GitHub API response did not include expected repository fields."
            ) from exc

        default_branch = str(repo.get("default_branch") or "HEAD")
        commits = api_get_optional_json(
            session,
            f"https://api.github.com/repos/{repository}/commits?sha={default_branch}&per_page=1",
            timeout=timeout,
        )
        latest_commit_date = None
        if commits:
            latest_commit_date = parse_github_datetime(
                commits[0].get("commit", {}).get("committer", {}).get("date")
            )

        license_present, license_name, license_key = public_license_info(
            session, repository, ref=default_branch, timeout=timeout
        )

        def fetch_content(path: str):
            return public_content(session, repository, path, ref=default_branch, timeout=timeout)

        documents = collect_documents(fetch_content)
        root_contents = public_root_contents(
            session, repository, ref=default_branch, timeout=timeout
        )
        descriptors = collect_descriptor_summaries(root_contents, fetch_content)

        try:
            return RepoHealth(
                full_name=full_name,
                html_url=html_url,
                archived=archived,
                status=repository_status(
                    archived=archived,
                    latest_commit_date=latest_commit_date,
                ),
                default_branch=default_branch,
                latest_commit_age=human_age(latest_commit_date),
                latest_commit_date=latest_commit_date,
                open_issue_count=public_search_count(
                    session, f"repo:{full_name} is:issue is:open", timeout=timeout
                ),
                open_pr_count=public_search_count(
                    session, f"repo:{full_name} is:pr is:open", timeout=timeout
                ),
                detected_language=repo.get("language"),
                license_present=license_present,
                license_name=license_name,
                license_key=license_key,
                readme_present=any(document.name == "README" for document in documents),
                ci_workflow_present=public_ci_workflow_present(
                    session, repository, ref=default_branch, timeout=timeout
                ),
                documents=documents,
                descriptors=descriptors,
            )
        except (KeyError, TypeError) as exc:
            raise GitHubApiError(
                "GitHub API response did not include expected repository fields."
            ) from exc
