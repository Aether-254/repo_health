# github-repo-health

[![Release](https://github.com/Aether-254/repo_health/actions/workflows/release.yml/badge.svg)](https://github.com/Aether-254/repo_health/actions/workflows/release.yml) [![ci](https://github.com/Aether-254/repo_health/actions/workflows/ci.yml/badge.svg)](https://github.com/Aether-254/repo_health/actions/workflows/ci.yml) [![codecov](https://codecov.io/github/Aether-254/repo_health/graph/badge.svg)](https://codecov.io/github/Aether-254/repo_health)

English | [中文](#中文)

## English

`github-repo-health` is a small Python 3.12 CLI app that scans a GitHub repository and prints a Rich terminal health summary.

It reports:

- archive status
- activity status for the default branch: active, semi-active, low activity, inactive, or archived
- latest commit age
- open issue count
- open pull request count
- detected language
- license presence, shortened to common SPDX-style names such as `MIT` when possible
- README presence
- GitHub Actions workflow presence
- README, code of conduct, contributing, license, and security documents rendered as terminal Markdown
- project descriptor summaries for files such as `pyproject.toml`, `package.json`, `go.mod`, `pom.xml`, `CMakeLists.txt`, and `Makefile`

### Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Copy the local environment template:

```bash
cp .env.example .env
```

`.env` is ignored by Git. The CLI reads environment variables directly:

```bash
set -a
source .env
set +a
```

### Usage

Public repositories use GitHub's REST API directly and do not require an API key:

```bash
repo-health openai/codex
```

Repository URLs are also accepted:

```bash
repo-health https://github.com/openai/codex
repo-health github.com/openai/codex
```

Private repositories use PyGithub and require `GITHUB_API_KEY` in `.env`:

```bash
python -m pip install -e ".[private]"
repo-health your-org/private-repo --private
```

Example output:

```text
Repository Health: openai/codex
Check                Result
Repository           https://github.com/openai/codex
Status               Active
Archived             No
Default branch       main
Latest commit age    3 days (2026-06-27)
Open issues          12
Open pull requests   4
Detected language    Python
License              MIT
README               Present
CI workflow          Present
```

### Development

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Install locally from source:

```bash
python -m pip install -e .
```

### Packaging

#### Shiv

Build an executable `.pyz`:

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

#### Nuitka

`src/github_requests_cli/cli.py` includes Nuitka project options. Build a one-file executable:

```bash
python -m nuitka src/github_requests_cli/cli.py
```

Output is written to `dist/nuitka/`.

#### PyInstaller

```bash
python -m PyInstaller --onefile --clean --name repo-health src/github_requests_cli/cli.py
```

### CI/CD

GitHub Actions includes:

- tests with `pytest`
- linting with `ruff check`
- formatting check with `ruff format --check`
- type checking with `mypy`
- live public repository scan
- Python package build
- Shiv `.pyz` build
- CodeQL analysis
- Dependabot version updates
- PyInstaller release binaries for:
  - `arm64darwin`
  - `arm64win`
  - `amd64win`
  - `x86win`
  - `amd64ubuntu`
  - `arm64ubuntu`

Pushing a tag matching `v*` publishes the generated artifacts to GitHub Releases.
Each release includes a `SHA256SUMS` file for artifact verification.

Verify a downloaded release artifact:

```bash
sha256sum -c SHA256SUMS
```

On macOS, if `sha256sum` is not installed:

```bash
shasum -a 256 -c SHA256SUMS
```

### File Guide

- `requirements.txt`: runtime dependencies.
- `requirements-dev.txt`: development, test, and packaging dependencies.
- `pyproject.toml`: project metadata, CLI entry point, tests, and tool configuration.
- `.gitignore`: ignores virtual environments, caches, build outputs, and local secrets.
- `.env.example`: local environment variable template.
- `CONTRIBUTING.md`: local development and PR checks.
- `CHANGELOG.md`: release notes.
- `CODE_OF_CONDUCT.md`: project collaboration standards.

## 中文

`github-repo-health` 是一个 Python 3.12 命令行工具，用于扫描 GitHub 仓库，并在终端中输出 Rich 格式的仓库健康摘要。

它会报告：

- 仓库是否已归档
- 默认分支活跃状态：活跃、半活跃、低活跃、不活跃或已归档
- 最近一次提交距今时间
- open issue 数量
- open pull request 数量
- 检测到的主要语言
- License 是否存在，并在可匹配时显示为 `MIT` 等常见 SPDX 风格缩写
- README 是否存在
- GitHub Actions workflow 是否存在
- 以终端 Markdown 渲染 README、行为准则、贡献指南、License 和安全策略文档
- 为 `pyproject.toml`、`package.json`、`go.mod`、`pom.xml`、`CMakeLists.txt`、`Makefile` 等描述文件生成摘要

### 环境准备

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

`.env` 已被 Git 忽略。CLI 会直接读取环境变量：

```bash
set -a
source .env
set +a
```

### 使用

公开仓库会直接使用 GitHub REST API，不需要 API key：

```bash
repo-health openai/codex
```

也支持仓库 URL：

```bash
repo-health https://github.com/openai/codex
```

私有仓库使用 PyGithub，并需要在 `.env` 中配置 `GITHUB_API_KEY`：

```bash
python -m pip install -e ".[private]"
repo-health your-org/private-repo --private
```

输出示例：

```text
Repository Health: openai/codex
Check                Result
Repository           https://github.com/openai/codex
Status               Active
Archived             No
Default branch       main
Latest commit age    3 days (2026-06-27)
Open issues          12
Open pull requests   4
Detected language    Python
License              MIT
README               Present
CI workflow          Present
```

### 开发

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

本地以源码方式安装：

```bash
python -m pip install -e .
```

### 打包

#### Shiv

生成可执行 `.pyz`：

```bash
python -m shiv \
  --site-packages .venv/lib/python3.12/site-packages \
  --compressed \
  --entry-point github_requests_cli.cli:main \
  --output-file dist/repo-health.pyz \
  .
```

运行：

```bash
python dist/repo-health.pyz --help
```

#### Nuitka

`src/github_requests_cli/cli.py` 已包含 Nuitka 项目选项。构建单文件可执行程序：

```bash
python -m nuitka src/github_requests_cli/cli.py
```

输出位于 `dist/nuitka/`。

#### PyInstaller

```bash
python -m PyInstaller --onefile --clean --name repo-health src/github_requests_cli/cli.py
```

### CI/CD

GitHub Actions 包含：

- 使用 `pytest` 运行测试
- 使用 `ruff check` 进行 lint
- 使用 `ruff format --check` 检查格式
- 使用 `mypy` 进行类型检查
- 公开仓库在线扫描
- Python 包构建
- Shiv `.pyz` 构建
- CodeQL 分析
- Dependabot 依赖更新
- PyInstaller 发布二进制，覆盖：
  - `arm64darwin`
  - `arm64win`
  - `amd64win`
  - `x86win`
  - `amd64ubuntu`
  - `arm64ubuntu`

推送匹配 `v*` 的 tag 会发布 GitHub Release。
每个 release 都包含用于校验产物的 `SHA256SUMS` 文件。

校验下载的 release 产物：

```bash
sha256sum -c SHA256SUMS
```

如果 macOS 上没有 `sha256sum`：

```bash
shasum -a 256 -c SHA256SUMS
```

### 文件说明

- `requirements.txt`：运行时依赖。
- `requirements-dev.txt`：开发、测试和打包依赖。
- `pyproject.toml`：项目元数据、命令行入口、测试和工具配置。
- `.gitignore`：忽略虚拟环境、缓存、构建产物和本地密钥。
- `.env.example`：本地环境变量模板。
- `CONTRIBUTING.md`：本地开发和 PR 检查流程。
- `CHANGELOG.md`：版本变更记录。
- `CODE_OF_CONDUCT.md`：项目协作行为规范。
