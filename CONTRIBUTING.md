# Contributing

## Local Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Copy local environment defaults if you need token-backed scans:

```bash
cp .env.example .env
```

## Checks

Run these before opening a pull request:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## Pull Requests

Keep changes focused and include tests for CLI behavior, network error handling, or release workflow changes when applicable.
