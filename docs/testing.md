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
