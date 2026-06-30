# nuitka-project: --mode=onefile
# nuitka-project: --output-dir=dist/nuitka
# nuitka-project: --output-filename=repo-health
# nuitka-project: --assume-yes-for-downloads
# nuitka-project: --follow-imports
"""Command line entrypoint for GitHub repository health summaries."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import requests
from github import Github, GithubException, UnknownObjectException

REPOSITORY_RE = re.compile(
    r"^(?:https?://github\.com/)?(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


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


class PublicRepositoryNotFoundError(RuntimeError):
    """Public REST API cannot read the repository."""


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_settings() -> Settings:
    load_dotenv()

    timeout = os.getenv("REQUEST_TIMEOUT_SECONDS", "20")
    try:
        request_timeout_seconds = float(timeout)
    except ValueError:
        request_timeout_seconds = 20.0

    return Settings(
        github_api_key=os.getenv("GITHUB_API_KEY") or os.getenv("GITHUB_TOKEN"),
        request_timeout_seconds=request_timeout_seconds,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-health",
        description="Print a Markdown health summary for any GitHub repository.",
    )
    parser.add_argument(
        "repository",
        help="GitHub repository as owner/name or https://github.com/owner/name.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub API key for private repositories. Defaults to GITHUB_API_KEY.",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Scan a private repository with PyGithub and a GitHub API key.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="HTTP timeout in seconds for API sanity checks. Defaults to REQUEST_TIMEOUT_SECONDS.",
    )
    return parser


def normalize_repository(value: str) -> str:
    match = REPOSITORY_RE.match(value.strip())
    if not match:
        raise ValueError("Repository must be in owner/name form or a github.com repository URL.")
    return f"{match.group('owner')}/{match.group('repo')}"


def github_client(token: str | None) -> Github:
    if not token:
        raise ValueError("Private repository scans require GITHUB_API_KEY in .env or --token.")
    return Github(token)


def github_headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_get_json(session: requests.Session, url: str, *, timeout: float):
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        raise PublicRepositoryNotFoundError("Repository is not public or does not exist.")
    response.raise_for_status()
    return response.json()


def api_get_optional_json(session: requests.Session, url: str, *, timeout: float):
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


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


def has_readme(repo) -> bool:
    try:
        repo.get_readme()
    except UnknownObjectException:
        return False
    return True


def has_ci_workflow(repo) -> bool:
    try:
        workflows = repo.get_contents(".github/workflows")
    except UnknownObjectException:
        return False

    if not isinstance(workflows, list):
        workflows = [workflows]

    return any(item.type == "file" and item.name.endswith((".yml", ".yaml")) for item in workflows)


def license_info(repo) -> tuple[bool, str | None]:
    try:
        license_file = repo.get_license()
    except UnknownObjectException:
        return False, None

    license_name = None
    if getattr(license_file, "license", None):
        license_name = getattr(license_file.license, "name", None)

    return True, license_name


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


def parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def public_search_count(session: requests.Session, query: str, *, timeout: float) -> int:
    response = session.get(
        "https://api.github.com/search/issues",
        params={"q": query, "per_page": 1},
        timeout=timeout,
    )
    if response.status_code == 404:
        raise PublicRepositoryNotFoundError("Repository is not public or does not exist.")
    response.raise_for_status()
    return int(response.json()["total_count"])


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
            ci_workflow_present=public_ci_workflow_present(session, repository, timeout=timeout),
        )


def present(value: bool) -> str:
    return "Present" if value else "Missing"


def render_markdown(health: RepoHealth) -> str:
    latest_commit = health.latest_commit_age
    if health.latest_commit_date is not None:
        latest_commit = (
            f"{health.latest_commit_age} ({health.latest_commit_date.date().isoformat()})"
        )

    license_value = "Present"
    if health.license_name:
        license_value = f"Present ({health.license_name})"
    elif not health.license_present:
        license_value = "Missing"

    return "\n".join(
        [
            f"# Repository Health: {health.full_name}",
            "",
            f"[View repository]({health.html_url})",
            "",
            "| Check | Result |",
            "| --- | --- |",
            f"| Archived | {'Yes' if health.archived else 'No'} |",
            f"| Latest commit age | {latest_commit} |",
            f"| Open issues | {health.open_issue_count} |",
            f"| Open pull requests | {health.open_pr_count} |",
            f"| Detected language | {health.detected_language or 'Unknown'} |",
            f"| License | {license_value} |",
            f"| README | {present(health.readme_present)} |",
            f"| CI workflow | {present(health.ci_workflow_present)} |",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings()

    try:
        repository = normalize_repository(args.repository)
        timeout = args.timeout or settings.request_timeout_seconds
        token = args.token or settings.github_api_key
        if args.private:
            health = scan_repository(github_client(token), repository)
        else:
            try:
                health = scan_public_repository(repository, timeout=timeout, token=token)
            except PublicRepositoryNotFoundError:
                if not token:
                    raise
                health = scan_repository(github_client(token), repository)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except PublicRepositoryNotFoundError as exc:
        print(
            f"{exc} For private repositories, set GITHUB_API_KEY in .env and pass --private.",
            file=sys.stderr,
        )
        return 2
    except requests.RequestException as exc:
        print(f"GitHub API is not reachable: {exc}", file=sys.stderr)
        return 1
    except GithubException as exc:
        print(f"GitHub API failed: {exc}", file=sys.stderr)
        return 1

    print(render_markdown(health))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
