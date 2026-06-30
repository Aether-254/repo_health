from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from github import UnknownObjectException

from github_requests_cli.cli import (
    RepoHealth,
    github_client,
    has_ci_workflow,
    human_age,
    load_dotenv,
    normalize_repository,
    parse_github_datetime,
    render_markdown,
)


def unknown_object() -> UnknownObjectException:
    return UnknownObjectException(404, {"message": "Not Found"}, None)


class FakeRepo:
    def __init__(self, contents):
        self.contents = contents

    def get_contents(self, path):
        if path != ".github/workflows" or self.contents is None:
            raise unknown_object()
        return self.contents


def test_normalize_repository_accepts_owner_name() -> None:
    assert normalize_repository("openai/codex") == "openai/codex"


def test_normalize_repository_accepts_github_url() -> None:
    assert normalize_repository("https://github.com/openai/codex.git") == "openai/codex"


def test_human_age_formats_days() -> None:
    now = datetime(2026, 6, 30, tzinfo=UTC)
    assert human_age(now - timedelta(days=12), now=now) == "12 days"


def test_parse_github_datetime() -> None:
    assert parse_github_datetime("2026-06-30T10:15:00Z") == datetime(
        2026, 6, 30, 10, 15, tzinfo=UTC
    )


def test_load_dotenv_sets_missing_values(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_API_KEY=ghp_test\n", encoding="utf-8")

    load_dotenv(env_file)

    assert __import__("os").environ["GITHUB_API_KEY"] == "ghp_test"


def test_private_github_client_requires_token() -> None:
    try:
        github_client(None)
    except ValueError as exc:
        assert "GITHUB_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing private token to fail")


def test_has_ci_workflow_detects_yaml_file() -> None:
    repo = FakeRepo([SimpleNamespace(type="file", name="ci.yml")])
    assert has_ci_workflow(repo) is True


def test_has_ci_workflow_missing_directory() -> None:
    repo = FakeRepo(None)
    assert has_ci_workflow(repo) is False


def test_render_markdown_includes_required_health_fields() -> None:
    markdown = render_markdown(
        RepoHealth(
            full_name="openai/codex",
            html_url="https://github.com/openai/codex",
            archived=False,
            latest_commit_age="3 days",
            latest_commit_date=datetime(2026, 6, 27, tzinfo=UTC),
            open_issue_count=12,
            open_pr_count=4,
            detected_language="Python",
            license_present=True,
            license_name="MIT License",
            readme_present=True,
            ci_workflow_present=False,
        )
    )

    assert "| Archived | No |" in markdown
    assert "| Latest commit age | 3 days (2026-06-27) |" in markdown
    assert "| Open issues | 12 |" in markdown
    assert "| Open pull requests | 4 |" in markdown
    assert "| CI workflow | Missing |" in markdown
