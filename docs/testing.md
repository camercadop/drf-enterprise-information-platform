# Testing

This document is the **reference inventory** for the test suite — what exists, how it's
configured, and what shared infrastructure is available. It answers: *"What does the test
suite look like?"*

It does not cover how to write a new test. For that, see
[Writing Tests](guidelines/writing-tests.md).

**What belongs here:**
- pytest configuration and settings
- Directory structure and file naming conventions
- Available fixtures and factories (inventory)
- Base class hierarchy and what each class provides (inventory)
- Patterns that exist in the codebase but aren't obvious from the code alone

**What belongs in [Writing Tests](guidelines/writing-tests.md) instead:**
- How to implement a test for a new endpoint
- How to write a factory or add a fixture
- How to assert responses correctly
- Decision guide for choosing the right base class

---

## Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific app
uv run pytest apps/iam_auth/

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
  iam_auth/
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
- Use `pytest-subtests` (`subtests` fixture) when a single test method asserts over multiple inputs — pass a descriptive label to `subtests.test()` so each failure is identifiable; see [Writing Tests — Subtests](guidelines/writing-tests.md#subtests)

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
- `superuser_membership` — links `superuser` to `tenant`
- `auth_client` — `APIClient` with JWT containing `tenant_id` claim
- `superuser_client` — same for superuser

## Base Test Classes

Reusable base classes live in `tests/base.py`. They provide automatic smoke tests
(connectivity verification) and template hooks for functional tests.

### Hierarchy

```
BaseAPITest                    # Foundation: self.client, self.user, self.membership
├── BaseActionAPITest          # Non-CRUD actions (login, logout, activate)
├── BaseCreateAPITest          # POST create
├── BaseRetrieveAPITest        # GET detail
├── BaseListAPITest            # GET list
├── BaseUpdateAPITest          # PATCH/PUT update
├── BaseDeleteAPITest          # DELETE
└── BaseCRUDAPITest            # All CRUD actions combined
```

### Smoke Tests

Every base class includes a smoke test that verifies the endpoint is reachable
and doesn't crash:

- Use no payload (empty request body)
- Use a random UUID for detail endpoints (no instance creation)
- Assert the response status is 2xx or 4xx (rejects 5xx and 3xx)
- Test connectivity only — no body or side-effect assertions

Smoke test names are distinct per action to avoid MRO conflicts:
- `BaseActionAPITest` → `test_smoke()`
- `BaseCreateAPITest` → `test_smoke_create()`
- `BaseRetrieveAPITest` → `test_smoke_retrieve()`
- `BaseListAPITest` → `test_smoke_list()`
- `BaseUpdateAPITest` → `test_smoke_update()`
- `BaseDeleteAPITest` → `test_smoke_delete()`

### Functional Tests (auto-generated)

Beyond smoke tests, the base classes provide functional tests using `pytest-subtests`:

- `test_create_valid` / `test_create_invalid` — iterates `valid_payloads()` and `invalid_payloads()`
- `test_retrieve_success` — creates instance, GETs it, calls `assert_valid_response()`
- `test_list_success` — creates instance, GETs list, asserts 200
- `test_update_valid` / `test_update_invalid` — iterates payloads against `update_instance()`
- `test_delete_success` — creates instance, DELETEs it, calls `assert_instance_deleted()`

### Template Hooks

Subclasses override these methods:

- `valid_payloads()` — list of valid data dicts for create/update
- `invalid_payloads()` — list of `(payload, expected_errors)` tuples
  - `expected_errors` can be `None` (only assert 400), a list of field names (`str`),
    or a list of dicts (`{field: error_code}`) for code-level assertions
- `create_instance()` — factory call to produce a test object
- `update_instance()` — instance for update tests (falls back to `create_instance()`)
- `detail_url(instance)` — URL for a specific resource (defaults to `url + pk + /`)
- `assert_instance_created(response)` — extra checks after creation
- `assert_valid_response(response)` — extra checks on retrieve
- `assert_instance_deleted(instance)` — verify soft-delete (defaults to checking `deleted_at`)

### Usage

```python
# Full CRUD viewset
class TestTenantViewSet(BaseCRUDAPITest):
    url = "/api/tenants/"

    def create_instance(self):
        return TenantFactory(tenant=self.membership.tenant)

    def valid_payloads(self):
        return [
            {"name": "Tenant A", "code": "tenant-a"},
            {"name": "Tenant B", "code": "tenant-b"},
        ]

    def invalid_payloads(self):
        return [
            ({}, ["name", "code"]),
            ({"name": ""}, ["name"]),
            ({"name": "X", "code": "has spaces"}, [{"code": "invalid"}]),
        ]

# Partial CRUD (list + retrieve only)
class TestReadOnlyViewSet(BaseListAPITest, BaseRetrieveAPITest):
    url = "/api/resources/"

    def create_instance(self):
        return ResourceFactory()

# Single action endpoint
class TestPasswordChangeView(BaseActionAPITest):
    url = "/api/auth/password/change/"

# Extra viewset action — separate class
class TestTenantActivate(BaseActionAPITest):
    url = "/api/tenants/{id}/activate/"
    http_method = "post"
```

### Service Layer Tests

Service-layer logic lives in `services.py` per app and is tested in `test_services.py`.
These tests are plain pytest classes — no base class needed. Use `@pytest.mark.django_db`
only when the service touches the database:

```python
@pytest.mark.django_db
class TestMyService:
    def test_does_something(self, membership):
        result = my_service_function(tenant=membership.tenant)
        assert result == expected
```

### Unauthenticated Endpoints

Endpoints that don't require auth (e.g., login, refresh) override `_setup_base`
to use `api_client` instead of `auth_client`:

```python
class TestLoginView(BaseActionAPITest):
    url = "/api/auth/login/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, api_client, user, membership):
        self.client = api_client
        self.user = user
        self.membership = membership
```

## Serializer Unit Tests

Use `make_serializer_with_tenant_context` from `tests/serializer_utils.py` to unit-test
serializers that rely on tenant or user context (e.g. `TenantInjectionSerializerPlugin`,
audit plugin) without going through the API layer:

```python
from tests.serializer_utils import make_serializer_with_tenant_context

@pytest.mark.django_db
class TestMySerializer:
    def test_valid(self, membership, user):
        serializer = make_serializer_with_tenant_context(
            MySerializer,
            {"field": "value"},
            membership,
            user,
        )
        assert serializer.is_valid(), serializer.errors
```

The helper builds a mock request with `request.auth["tenant_id"]` and `request.user` set,
matching what the global plugins expect at runtime.

## Unit Test Patterns

### Mocking with `MagicMock`

Use `unittest.mock.MagicMock` to isolate units from their dependencies without hitting
the database or external services:

```python
from unittest.mock import MagicMock

class TestMyProcessor:
    def test_sets_field_on_session(self):
        session = MagicMock()
        MyProcessor().process(session, io.BytesIO(b"data"))
        assert session.some_field == expected
```

### Overriding settings per test

Use `django.test.override_settings` for settings-driven behavior:

```python
from django.test import override_settings

class TestMyValidator:
    def test_raises_when_limit_exceeded(self):
        with override_settings(MY_APP={"MAX_SIZE": 1024}):
            with pytest.raises(ValidationError):
                validate_size(2048)
```

Use pytest-django's `settings` fixture for inline per-test overrides:

```python
class TestMyLogic:
    def test_threshold_enforced(self, settings):
        settings.MY_APP = {"MAX_ATTEMPTS": 3}
        # test body
```

### Patching module-level dependencies

Use `unittest.mock.patch` to replace a dependency for the duration of a test:

```python
from unittest.mock import patch

class TestMyView:
    def test_behaviour_when_flag_set(self):
        with patch("apps.my_app.module.settings") as mock_settings:
            mock_settings.MY_FEATURE = {"ENABLED": True}
            # test body
```

## Cache-Dependent Tests

Tests that exercise cache-backed logic (lockout, session limits, idempotency) must
clear the cache before each test to prevent state leakage between runs:

```python
from django.core.cache import cache
import pytest

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
```

Place this fixture at the class or module level. Since `config.settings.test` replaces
Redis with `LocMemCache`, `cache.clear()` is fast and safe in all environments.
