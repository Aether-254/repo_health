"""Markdown rendering for repository health results."""

from __future__ import annotations

from github_requests_cli.models import RepoHealth


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
