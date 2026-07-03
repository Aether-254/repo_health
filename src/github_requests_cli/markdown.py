"""Legacy text rendering helpers for repository health results."""

from __future__ import annotations

from github_requests_cli.rich_render import license_display, present


def render_markdown(health) -> str:
    """Return a plain text summary.

    The CLI uses Rich for terminal output. This helper remains available for
    callers that imported the old name before the renderer changed.
    """
    latest_commit = health.latest_commit_age
    if health.latest_commit_date is not None:
        latest_commit = (
            f"{health.latest_commit_age} ({health.latest_commit_date.date().isoformat()})"
        )

    return "\n".join(
        [
            f"Repository Health: {health.full_name}",
            f"Repository: {health.html_url}",
            f"Status: {health.status}",
            f"Archived: {'Yes' if health.archived else 'No'}",
            f"Default branch: {health.default_branch}",
            f"Latest commit age: {latest_commit}",
            f"Open issues: {health.open_issue_count}",
            f"Open pull requests: {health.open_pr_count}",
            f"Detected language: {health.detected_language or 'Unknown'}",
            f"License: {license_display(health)}",
            f"README: {present(health.readme_present)}",
            f"CI workflow: {present(health.ci_workflow_present)}",
            "",
        ]
    )
