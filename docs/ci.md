# Continuous Integration

Automated quality gates that run on every code change. The CI pipeline ensures that no code reaches `dev` or `main` without passing lint, type checks, schema validation, and tests.

GitHub Actions runs automatically on pushes to `main`/`dev` and PRs targeting either branch.

## Pipeline

1. `ruff check .` — Linting
2. `mypy .` — Type checking
3. `manage.py check_permission_catalog` — Validate permission declarations
4. `manage.py check_tenant_settings_catalog` — Validate tenant settings declarations
5. `manage.py spectacular --validate --fail-on-warn` — Validate OpenAPI schema
6. `manage.py migrate` — Apply database migrations
7. `pytest` — Tests (against PostgreSQL 16, using `config.settings.test`)

## Branching Strategy

- `main` — production-ready code. Only receives merges from `dev`.
- `dev` — active development. All feature/fix branches target `dev`.

## Workflow File

`.github/workflows/ci.yml`
