# github-repo-health

A small Python 3.12 CLI app that scans any GitHub repository and prints a clean health summary as Markdown.

It reports:

- archived status
- latest commit age
- open issue count
- open pull request count
- detected language
- license presence
- README presence
- GitHub Actions workflow presence

## 环境准备

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

复制本地配置模板：

```bash
cp .env.example .env
```

`.env` is ignored by Git. The CLI reads environment variables directly:

```bash
set -a
source .env
set +a
```

## Usage

Public repositories use GitHub's REST API directly and do not require an API key:

```bash
repo-health openai/codex
```

Repository URLs are also accepted:

```bash
repo-health https://github.com/openai/codex
```

Private repositories use PyGithub and require `GITHUB_API_KEY` in `.env`:

```bash
python -m pip install -e ".[private]"
repo-health your-org/private-repo --private
```

Example output:

```markdown
# Repository Health: openai/codex

[View repository](https://github.com/openai/codex)

| Check | Result |
| --- | --- |
| Archived | No |
| Latest commit age | 3 days (2026-06-27) |
| Open issues | 12 |
| Open pull requests | 4 |
| Detected language | Python |
| License | Present (MIT License) |
| README | Present |
| CI workflow | Present |
```

## 开发

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

本地以源码方式安装：

```bash
python -m pip install -e .
```

## 打包

### Shiv

生成可执行 `.pyz`：

```bash
python -m shiv \
  --site-packages .venv/lib/python3.12/site-packages \
  --compressed \
  --entry-point github_requests_cli.cli:main \
  --output-file dist/repo-health.pyz \
  .
```

Run:

```bash
python dist/repo-health.pyz --help
```

### Nuitka

`src/github_requests_cli/cli.py` 已包含 Nuitka 项目选项。构建单文件可执行程序：

```bash
python -m nuitka src/github_requests_cli/cli.py
```

输出位于 `dist/nuitka/`。

### PyInstaller

```bash
python -m PyInstaller --onefile --clean --name repo-health src/github_requests_cli/cli.py
```

## CI/CD

GitHub Actions includes:

- tests with `pytest`
- linting with `ruff check`
- formatting check with `ruff format --check`
- live public repository scan
- Python package build
- Shiv `.pyz` build
- CodeQL default setup
- Dependabot version updates
- PyInstaller release binaries for:
  - `arm64darwin`
  - `amd64darwin`
  - `arm64win`
  - `amd64win`
  - `x86win`
  - `amd64ubuntu`
  - `arm64ubuntu`

Pushing a tag matching `v*` publishes the generated artifacts to GitHub Releases.

## 文件说明

- `requirements.txt`：运行时依赖。
- `requirements-dev.txt`：开发、测试和打包依赖。
- `pyproject.toml`：项目元数据、命令行入口、测试和 Nuitka 配置。
- `.gitignore`：忽略虚拟环境、缓存、构建产物和本地密钥。
- `.env.example`：本地环境变量模板。
