# Testing

## Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific app
uv run pytest apps/authentication/

# Run tests for core
uv run pytest core/tests/

# Run a specific test file
uv run pytest apps/tenants/tests/test_utils.py

# Run only tests that don't need DB
uv run pytest -m "not django_db"
```

## Settings

Tests use `config.settings.test`, which:

- Sets `DATABASE_URL` and `REDIS_URL` defaults via `os.environ.setdefault` (won't override CI env vars)
- Replaces Redis cache with `LocMemCache` to avoid requiring a running Redis instance

This is configured in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Structure

Tests live next to the code they test:

```
core/
  tests/
    test_exceptions.py
    test_permissions.py
    ...

apps/
  authentication/
    tests/
      test_api_login.py
      test_api_logout.py
      ...
  tenants/
    tests/
      test_api_tenants.py
      test_utils.py
      ...

tests/
  factories/          # Factory Boy factories, split per app
    users.py
    tenants.py
  fixtures/           # Shared pytest fixtures, split per domain
    clients.py
    users.py
    tenants.py
  conftest.py         # Wires fixture modules via pytest_plugins
```

## Conventions

- Test classes use `Test*` prefix, test functions use `test_*` prefix
- Pytest-style classes with bare `assert` (no `unittest.TestCase`)
- Use `@pytest.mark.django_db` only when the test actually needs the database
- Pure logic tests (validators, formatters, security utils) should not require DB access
- Endpoint (integration) test files use the `test_api_*` prefix (e.g., `test_api_login.py`)
- Factories split per app under `tests/factories/<app>.py`
- Shared fixtures split per domain under `tests/fixtures/<domain>.py`

## Factories

Factories use [Factory Boy](https://factoryboy.readthedocs.io/):

```python
from tests.factories.users import UserFactory
from tests.factories.tenants import TenantFactory
```

## Fixtures

Shared fixtures are defined in `tests/fixtures/` and wired via `pytest_plugins` in `tests/conftest.py`:

- `api_client` — bare `APIClient` instance
- `user` — a standard user
- `superuser` — a superuser
- `tenant` — a tenant
- `role` — a tenant role
- `membership` — links `user` to `tenant`
- `auth_client` — `APIClient` with JWT containing `tenant_id` claim
- `superuser_client` — same for superuser
