# Testing

## Running Tests

```bash
# Run all tests
uv run pytest

# Run only unit tests (no DB required)
uv run pytest tests/unit -m "not django_db"

# Run only DB-dependent unit tests (requires PostgreSQL)
uv run pytest tests/unit -m django_db

# Run a specific test file
uv run pytest path/to/test_file.py
```

## Settings

Tests use `config.settings.test`, which:

- Sets `DATABASE_URL` and `REDIS_URL` defaults via `os.environ.setdefault` (won't override CI env vars)
- Replaces Redis cache with `LocMemCache` to avoid requiring a running Redis instance

This is configured in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Structure

The `tests/` directory mirrors the source tree. Each test file maps to a source module with a `test_` prefix (e.g., `core/utils/security.py` -> `tests/unit/core/test_utils_security.py`).

- `unit/` — isolated tests, minimal or no DB access
- `integration/` — full request/response cycle through API endpoints (planned)

## Conventions

- Test classes use `Test*` prefix, test functions use `test_*` prefix
- Use `@pytest.mark.django_db` only when the test actually needs the database
- Pure logic tests (validators, formatters, security utils) should not require DB access
