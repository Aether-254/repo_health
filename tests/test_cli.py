from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import requests

from github_requests_cli.cli import (
    PublicRepositoryNotFoundError,
    RepoHealth,
    api_get_json,
    github_client,
    has_ci_workflow,
    human_age,
    load_dotenv,
    main,
    normalize_repository,
    parse_github_datetime,
    public_search_count,
    render_markdown,
    scan_public_repository,
)


class UnknownObjectException(Exception):
    status = 404


def unknown_object() -> UnknownObjectException:
    return UnknownObjectException("Not Found")


class FakeRepo:
    def __init__(self, contents):
        self.contents = contents

    def get_contents(self, path):
        if path != ".github/workflows" or self.contents is None:
            raise unknown_object()
        return self.contents


class FakeResponse:
    def __init__(self, payload, *, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.headers = {}
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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


def test_scan_public_repository_uses_rest_api(monkeypatch) -> None:
    session = FakeSession(
        [
            FakeResponse(
                {
                    "full_name": "openai/codex",
                    "html_url": "https://github.com/openai/codex",
                    "archived": False,
                    "language": "Python",
                }
            ),
            FakeResponse(
                [
                    {
                        "commit": {
                            "committer": {
                                "date": "2026-06-30T10:15:00Z",
                            }
                        }
                    }
                ]
            ),
            FakeResponse({"license": {"name": "MIT License"}}),
            FakeResponse({"total_count": 7}),
            FakeResponse({"total_count": 2}),
            FakeResponse({"name": "README.md"}),
            FakeResponse(
                [
                    {"type": "file", "name": "ci.yml"},
                    {"type": "file", "name": "notes.txt"},
                ]
            ),
        ]
    )
    monkeypatch.setattr("github_requests_cli.cli.requests.Session", lambda: session)

    health = scan_public_repository("openai/codex", timeout=3, token="ghp_test")

    assert health == RepoHealth(
        full_name="openai/codex",
        html_url="https://github.com/openai/codex",
        archived=False,
        latest_commit_age=human_age(datetime(2026, 6, 30, 10, 15, tzinfo=UTC)),
        latest_commit_date=datetime(2026, 6, 30, 10, 15, tzinfo=UTC),
        open_issue_count=7,
        open_pr_count=2,
        detected_language="Python",
        license_present=True,
        license_name="MIT License",
        readme_present=True,
        ci_workflow_present=True,
    )
    assert session.headers["Authorization"] == "Bearer ghp_test"
    assert session.calls[0] == ("https://api.github.com/repos/openai/codex", {"timeout": 3})
    assert session.calls[3][1]["params"] == {
        "q": "repo:openai/codex is:issue is:open",
        "per_page": 1,
    }


def test_api_get_json_raises_public_not_found_on_404() -> None:
    session = FakeSession([FakeResponse({"message": "Not Found"}, status_code=404)])

    try:
        api_get_json(session, "https://api.github.com/repos/missing/repo", timeout=3)
    except PublicRepositoryNotFoundError as exc:
        assert "not public" in str(exc)
    else:
        raise AssertionError("Expected public repository lookup to fail")


def test_public_search_count_raises_public_not_found_on_404() -> None:
    session = FakeSession([FakeResponse({"message": "Not Found"}, status_code=404)])

    try:
        public_search_count(session, "repo:missing/repo is:issue is:open", timeout=3)
    except PublicRepositoryNotFoundError as exc:
        assert "not public" in str(exc)
    else:
        raise AssertionError("Expected public search lookup to fail")


def test_main_reports_public_not_found_without_token(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "github_requests_cli.cli.load_settings",
        lambda: SimpleNamespace(
            github_api_key=None,
            request_timeout_seconds=3,
        ),
    )
    monkeypatch.setattr(
        "github_requests_cli.cli.scan_public_repository",
        lambda repository, *, timeout, token=None: (_ for _ in ()).throw(
            PublicRepositoryNotFoundError("Repository is not public or does not exist.")
        ),
    )

    assert main(["missing/repo"]) == 2

    captured = capsys.readouterr()
    assert "For private repositories" in captured.err


def test_main_falls_back_to_private_scan_when_public_scan_fails_with_token(
    monkeypatch, capsys
) -> None:
    expected = RepoHealth(
        full_name="private/repo",
        html_url="https://github.com/private/repo",
        archived=False,
        latest_commit_age="No commits found",
        latest_commit_date=None,
        open_issue_count=0,
        open_pr_count=0,
        detected_language=None,
        license_present=False,
        license_name=None,
        readme_present=False,
        ci_workflow_present=False,
    )
    monkeypatch.setattr(
        "github_requests_cli.cli.load_settings",
        lambda: SimpleNamespace(
            github_api_key="ghp_test",
            request_timeout_seconds=3,
        ),
    )
    monkeypatch.setattr(
        "github_requests_cli.cli.scan_public_repository",
        lambda repository, *, timeout, token=None: (_ for _ in ()).throw(
            PublicRepositoryNotFoundError("Repository is not public or does not exist.")
        ),
    )
    monkeypatch.setattr("github_requests_cli.cli.github_client", lambda token: "client")
    monkeypatch.setattr(
        "github_requests_cli.cli.scan_repository",
        lambda client, repository: expected,
    )

    assert main(["private/repo"]) == 0

    captured = capsys.readouterr()
    assert "# Repository Health: private/repo" in captured.out


def test_main_reports_request_exception(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "github_requests_cli.cli.load_settings",
        lambda: SimpleNamespace(
            github_api_key=None,
            request_timeout_seconds=3,
        ),
    )
    monkeypatch.setattr(
        "github_requests_cli.cli.scan_public_repository",
        lambda repository, *, timeout, token=None: (_ for _ in ()).throw(
            requests.Timeout("timed out")
        ),
    )

    assert main(["openai/codex"]) == 1

    captured = capsys.readouterr()
    assert "GitHub API is not reachable" in captured.err
