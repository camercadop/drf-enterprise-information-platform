# Continuous Integration

GitHub Actions runs automatically on pushes to `main` and PRs targeting `main`.

## Pipeline

1. `ruff check .` — Linting
2. `mypy .` — Type checking
3. `pytest` — Tests (against PostgreSQL 16, using `config.settings.test`)

## Workflow File

`.github/workflows/ci.yml`
