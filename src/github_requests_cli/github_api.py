"""Low-level GitHub REST API helpers."""

from __future__ import annotations

from typing import Any

import requests

from github_requests_cli.errors import GitHubApiError, PublicRepositoryNotFoundError


def github_headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def response_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if isinstance(payload, dict):
        return str(payload.get("message") or "")
    return ""


def raise_for_github_status(response: requests.Response) -> None:
    if response.status_code == 404:
        raise PublicRepositoryNotFoundError("Repository is not public or does not exist.")
    if response.status_code == 401:
        raise GitHubApiError("GitHub API authentication failed. Check --token or GITHUB_API_KEY.")
    if response.status_code == 403:
        message = response_message(response).lower()
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0" or "rate limit" in message:
            raise GitHubApiError("GitHub API rate limit exceeded. Retry later or pass --token.")
        raise GitHubApiError("GitHub API access forbidden. Check repository access or token scope.")
    if response.status_code == 422:
        raise GitHubApiError("GitHub API rejected the search query for this repository.")
    if response.status_code >= 500:
        raise GitHubApiError(f"GitHub API server error ({response.status_code}). Try again later.")

    response.raise_for_status()


def response_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise GitHubApiError("GitHub API returned malformed JSON.") from exc


def api_get_json(session: requests.Session, url: str, *, timeout: float):
    response = session.get(url, timeout=timeout)
    raise_for_github_status(response)
    return response_json(response)


def api_get_optional_json(session: requests.Session, url: str, *, timeout: float):
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    raise_for_github_status(response)
    return response_json(response)
