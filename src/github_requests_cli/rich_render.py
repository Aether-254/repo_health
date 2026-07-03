"""Rich terminal rendering for repository health results."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from github_requests_cli.license_utils import short_license_name
from github_requests_cli.models import RepoHealth


def present(value: bool) -> str:
    return "Present" if value else "Missing"


def license_display(health: RepoHealth) -> str:
    if not health.license_present:
        return "Missing"
    return short_license_name(health.license_name, health.license_key) or "Present"


def render_health(health: RepoHealth, *, console: Console | None = None) -> None:
    console = console or Console()
    console.print(summary_table(health))

    if health.descriptors:
        console.print(descriptor_table(health))

    for document in health.documents:
        console.print(
            Panel(
                Markdown(document.markdown),
                title=f"{document.name}: {document.path}",
                expand=False,
            )
        )


def summary_table(health: RepoHealth) -> Table:
    table = Table(title=f"Repository Health: {health.full_name}", show_header=True)
    table.add_column("Check", style="bold")
    table.add_column("Result")

    latest_commit = health.latest_commit_age
    if health.latest_commit_date is not None:
        latest_commit = (
            f"{health.latest_commit_age} ({health.latest_commit_date.date().isoformat()})"
        )

    table.add_row("Repository", health.html_url)
    table.add_row("Status", health.status)
    table.add_row("Archived", "Yes" if health.archived else "No")
    table.add_row("Default branch", health.default_branch)
    table.add_row("Latest commit age", latest_commit)
    table.add_row("Open issues", str(health.open_issue_count))
    table.add_row("Open pull requests", str(health.open_pr_count))
    table.add_row("Detected language", health.detected_language or "Unknown")
    table.add_row("License", license_display(health))
    table.add_row("README", present(health.readme_present))
    table.add_row("CI workflow", present(health.ci_workflow_present))
    return table


def descriptor_table(health: RepoHealth) -> Table:
    table = Table(title="Repository Descriptors", show_header=True)
    table.add_column("File", style="bold")
    table.add_column("Type")
    table.add_column("Summary")
    for descriptor in health.descriptors:
        table.add_row(descriptor.path, descriptor.kind, "; ".join(descriptor.summary))
    return table
