# nuitka-project: --mode=onefile
# nuitka-project: --output-dir=dist/nuitka
# nuitka-project: --output-filename=repo-health
# nuitka-project: --assume-yes-for-downloads
# nuitka-project: --follow-imports
"""Command line entrypoint for GitHub repository health summaries."""

from __future__ import annotations

import argparse
import sys

import requests

from github_requests_cli.errors import GitHubApiError, PublicRepositoryNotFoundError
from github_requests_cli.github_api import api_get_json, api_get_optional_json
from github_requests_cli.markdown import present, render_markdown
from github_requests_cli.models import GithubClient, RepoHealth, Settings
from github_requests_cli.private_scan import (
    github_client,
    has_ci_workflow,
    has_readme,
    is_github_not_found,
    latest_commit_datetime,
    license_info,
    scan_repository,
    total_search_count,
)
from github_requests_cli.public_scan import public_search_count, scan_public_repository
from github_requests_cli.repositories import normalize_repository
from github_requests_cli.settings import load_dotenv, load_settings
from github_requests_cli.time_utils import human_age, parse_github_datetime

__all__ = [
    "GitHubApiError",
    "GithubClient",
    "PublicRepositoryNotFoundError",
    "RepoHealth",
    "Settings",
    "api_get_json",
    "api_get_optional_json",
    "github_client",
    "has_ci_workflow",
    "has_readme",
    "human_age",
    "is_github_not_found",
    "latest_commit_datetime",
    "license_info",
    "load_dotenv",
    "load_settings",
    "main",
    "normalize_repository",
    "parse_github_datetime",
    "present",
    "public_search_count",
    "render_markdown",
    "scan_public_repository",
    "scan_repository",
    "total_search_count",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-health",
        description="Print a Markdown health summary for any GitHub repository.",
    )
    parser.add_argument(
        "repository",
        help="GitHub repository as owner/name, github.com/owner/name, or https://github.com/owner/name.",
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
    except GitHubApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"GitHub API is not reachable: {exc}. Try increasing --timeout.", file=sys.stderr)
        return 1
    except Exception as exc:
        if not exc.__class__.__module__.startswith("github"):
            raise
        print(f"GitHub API failed: {exc}", file=sys.stderr)
        return 1

    print(render_markdown(health))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
