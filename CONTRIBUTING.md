# Contributing

Thank you for your interest in contributing to the DRF Enterprise Information Platform.

## Prerequisites

- Python 3.14+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/)
- Familiarity with [Django REST Framework](https://www.django-rest-framework.org/)

## Getting Started

```bash
git clone <repository-url>
cd drf-enterprise-information-platform
docker compose up -d
uv sync
uv run python manage.py migrate
uv run pre-commit install
```

See [docs/development.md](docs/development.md) for full setup details.

## Workflow

1. Create a branch from `dev` using the naming convention below.
2. Make your changes following the project's [code style](docs/code-style.md).
3. Run quality checks before pushing.
4. Open a pull request targeting `dev`.

## Branching Strategy

- `main` — production-ready code. Only receives merges from `dev`.
- `dev` — active development. All feature/fix branches target `dev`.
- Feature branches are short-lived and deleted after merge.

## Branch Naming

```
feat/short-description     # New feature
fix/short-description      # Bug fix
docs/short-description     # Documentation only
refactor/short-description # Code restructuring without behavior change
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add tenant invitation endpoint
fix: prevent duplicate membership on concurrent requests
docs: add soft-delete guideline
refactor: extract token validation to shared utility
```

- Use imperative mood ("add", not "added")
- Keep the subject line under 72 characters
- Add a body for non-trivial changes explaining *why*, not *what*

## Quality Checks

All checks must pass before a PR is merged:

```bash
uv run ruff check .              # Lint
uv run ruff format --check .     # Format verification
uv run mypy .                    # Type check
uv run pytest                    # Tests
```

Pre-commit hooks run these automatically on staged files.

## Continuous Integration

A GitHub Actions workflow runs automatically on every push to `main`/`dev` and on PRs targeting either branch. Your PR must pass all checks before merge:

| Step | What it does |
|------|--------------|
| Lint | `ruff check .` |
| Type check | `mypy .` |
| Permission catalog | Validates permission declarations are consistent |
| OpenAPI schema | Validates the schema with `drf-spectacular` |
| Migrate | Ensures migrations apply cleanly |
| Test | `pytest` against PostgreSQL 16 |

If CI fails, check the workflow logs — fix locally before pushing again.

## Pull Request Guidelines

- One logical change per PR — don't bundle unrelated work
- Include tests for new behavior
- Update documentation if the change affects public interfaces or developer workflow
- Reference related issues in the PR description
- Keep PRs small and reviewable (under 400 lines when possible)

## Architectural Changes

Changes that affect how the system is structured or how components interact require an Architecture Decision Record (ADR) **before** implementation begins.

See [docs/adr/README.md](docs/adr/README.md) for:

- When an ADR is warranted
- Writing guidelines
- The ADR template

## Adding a New Domain Module

Follow the [Creating a New App](docs/guidelines/creating-a-new-app.md) guideline. Key rules:

- All modules live in `apps/`
- Inherit from `core/` base classes — never modify `core/` for module-specific needs
- Each module owns its models, serializers, views, and URLs
- No direct imports between modules

## Code Review Expectations

Reviewers check for:

- Adherence to [code style](docs/code-style.md) and [architecture](docs/architecture.md)
- No ADR violations
- Test coverage for new behavior
- No security regressions (tenant isolation, auth, input validation)
- Clear naming and minimal comments

## Reporting Issues

When reporting a bug, include:

- Steps to reproduce
- Expected vs actual behavior
- Python version, OS, and relevant environment details
- Error output or logs

## Questions

If something is unclear, open an issue with the `question` label rather than guessing. The documentation should answer most questions — if it doesn't, that's a documentation bug.
