# Writing Tests

How to write tests in this project — from choosing the right base class and wiring fixtures to structuring assertions and handling edge cases like unauthenticated endpoints.

---

## Overview

Tests live next to the code they test (`apps/<app>/tests/`). Shared infrastructure lives in `tests/`:

```
tests/
  base.py              # Base test classes (smoke + functional)
  factories/           # Factory Boy factories, one file per app
  fixtures/            # Shared pytest fixtures, one file per domain
  conftest.py          # Wires fixture modules via pytest_plugins
```

Two categories of tests:

| Category | File prefix | Needs DB? | Example |
|----------|-------------|-----------|---------|
| Unit (pure logic) | `test_*.py` | No | `test_utils.py`, `test_plugins.py` |
| Integration (API) | `test_api_*.py` | Yes | `test_api_login.py`, `test_api_tenants.py` |

---

## Unit Tests

Use for pure logic that does not touch the database: validators, formatters, utility functions, permission logic.

```python
from unittest.mock import MagicMock

from apps.tenants.utils import get_tenant_id


class TestGetTenantId:
    def test_extracts_tenant_id_from_auth(self) -> None:
        request = MagicMock()
        request.auth = {"tenant_id": "abc-123"}
        assert get_tenant_id(request) == "abc-123"

    def test_returns_none_when_no_auth(self) -> None:
        request = MagicMock()
        request.auth = None
        assert get_tenant_id(request) is None
```

Key rules:

- Do not use `@pytest.mark.django_db`
- Use `MagicMock` or plain objects to simulate dependencies
- Group related tests in a `Test*` class

---

## Integration Tests (API)

Use the base test classes from `tests/base.py`. They provide automatic smoke tests and functional test templates.

### CRUD Endpoint

```python
from tests.base import BaseCRUDAPITest
from tests.factories.tenants import TenantFactory


class TestTenantViewSet(BaseCRUDAPITest):
    url = "/api/tenants/"

    def create_instance(self):
        return TenantFactory(tenant=self.membership.tenant)

    def valid_payloads(self):
        return [
            {"name": "Tenant A", "code": "tenant-a"},
        ]

    def invalid_payloads(self):
        return [
            ({}, ["name", "code"]),
            ({"name": ""}, ["name"]),
            ({"name": "X", "code": "has spaces"}, [{"code": "invalid"}]),
        ]
```

This single class generates:

- `test_smoke_create`, `test_smoke_retrieve`, `test_smoke_list`, `test_smoke_update`, `test_smoke_delete`
- `test_create_valid`, `test_create_invalid`
- `test_retrieve_success`
- `test_list_success`
- `test_update_valid`, `test_update_invalid`
- `test_delete_success`

### Partial CRUD (read-only)

```python
from tests.base import BaseListAPITest, BaseRetrieveAPITest
from tests.factories.tenants import TenantFactory


class TestTenantReadOnly(BaseListAPITest, BaseRetrieveAPITest):
    url = "/api/tenants/"

    def create_instance(self):
        return TenantFactory()
```

### Single Action Endpoint

```python
from tests.base import BaseActionAPITest


class TestPasswordChangeView(BaseActionAPITest):
    url = "/api/auth/password/change/"
```

### Unauthenticated Endpoints

Override `_setup_base` to use `api_client` instead of `auth_client`:

```python
import pytest
from rest_framework.test import APIClient

from apps.iam_users.models import TenantMembership, User
from tests.base import BaseActionAPITest


class TestLoginView(BaseActionAPITest):
    url = "/api/auth/login/"

    @pytest.fixture(autouse=True)
    def _setup_base(self, api_client: APIClient, user: User, membership: TenantMembership) -> None:  # type: ignore[override]
        self.client = api_client
        self.user = user
        self.membership = membership
```

### Custom Assertions

Override template hooks for domain-specific checks:

```python
from typing import Any

from tests.base import BaseCreateAPITest


class TestInvoiceCreate(BaseCreateAPITest):
    url = "/api/invoices/"

    def valid_payloads(self):
        return [{"number": "INV-001", "amount": "100.00"}]

    def invalid_payloads(self):
        return [({}, ["number", "amount"])]

    def assert_instance_created(self, response: Any) -> None:
        assert response.data["number"] == "INV-001"
```

### Extra ViewSet Actions

Test custom actions (e.g., `activate`, `deactivate`) as separate `BaseActionAPITest` classes:

```python
from tests.base import BaseActionAPITest
from tests.factories.tenants import TenantMembershipFactory


class TestMembershipDeactivate(BaseActionAPITest):
    url = ""  # Set dynamically
    http_method = "post"

    @pytest.fixture(autouse=True)
    def _setup_action(self, auth_client, user, membership):
        self.client = auth_client
        self.user = user
        self.membership = membership
        target = TenantMembershipFactory(tenant=membership.tenant)
        self.url = f"/api/memberships/{target.pk}/deactivate/"
```

---

## Factories

Factories live in `tests/factories/<app>.py`. Use [Factory Boy](https://factoryboy.readthedocs.io/).

### Writing a Factory

```python
import factory

from apps.invoices.models import Invoice
from tests.factories.tenants import TenantFactory


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    tenant = factory.SubFactory(TenantFactory)
    number = factory.Sequence(lambda n: f"INV-{n:04d}")
    amount = factory.LazyFunction(lambda: "100.00")
```

### Rules

- One factory file per app: `tests/factories/<app_name>.py`
- Use `factory.Sequence` for unique fields
- Use `factory.SubFactory` for FK relationships
- Use `factory.SelfAttribute` to reference parent attributes in nested sub-factories
- Default password for users: `"TestPass123!"`

---

## Fixtures

Shared fixtures live in `tests/fixtures/<domain>.py` and are wired via `pytest_plugins` in `tests/conftest.py`.

### Available Fixtures

| Fixture | Returns | Description |
|---------|---------|-------------|
| `api_client` | `APIClient` | Bare client, no auth |
| `auth_client` | `APIClient` | JWT with `tenant_id` claim |
| `superuser_client` | `APIClient` | JWT for superuser |
| `user` | `User` | Standard active user |
| `superuser` | `User` | Superuser |
| `tenant` | `Tenant` | Active tenant |
| `role` | `TenantRole` | Role in the test tenant |
| `membership` | `TenantMembership` | Links `user` to `tenant` |

### Adding a Fixture

Add domain-specific fixtures to `tests/fixtures/<domain>.py`:

```python
# tests/fixtures/invoices.py
import pytest

from apps.invoices.models import Invoice
from tests.factories.invoices import InvoiceFactory


@pytest.fixture()
def invoice(membership) -> Invoice:
    return InvoiceFactory(tenant=membership.tenant)
```

Then register the module in `tests/conftest.py`:

```python
pytest_plugins = [
    "tests.fixtures.users",
    "tests.fixtures.tenants",
    "tests.fixtures.clients",
    "tests.fixtures.invoices",  # Add here
]
```

---

## invalid_payloads Format

The second element of each tuple controls assertion depth:

| Value | Behavior |
|-------|----------|
| `None` | Assert 400 only, no field checks |
| `["field_a", "field_b"]` | Assert those fields are present in the error response |
| `[{"field": "error_code"}]` | Assert the field has a specific DRF error code |

```python
def invalid_payloads(self):
    return [
        ({}, None),                                    # Just check 400
        ({"name": ""}, ["name"]),                      # Check field presence
        ({"code": "has spaces"}, [{"code": "invalid"}]),  # Check error code
    ]
```

---

## Asserting 400 Responses in Standalone Tests

When writing `@pytest.mark.django_db` tests outside `BaseCRUDAPITest`, always assert beyond the status code. A bare `assert response.status_code == 400` passes for any validation failure — including ones caused by unrelated bugs.

Two levels of precision, in order of preference:

**1. Assert the error code (preferred)**

DRF wraps validation errors in `ErrorDetail` objects that carry a `code`. Asserting the code is stable — it won't break if the human-readable message is reworded.

```python
# Non-field errors land in GLOBAL_ERRORS
assert response.data["data"]["GLOBAL_ERRORS"][0].code == "already_exists"

# Field errors land under the field name
assert response.data["data"]["kind"][0].code == "invalid"
```

Error codes are defined at the validator or serializer level (e.g., `UniqueTogetherContextValidator(code="already_exists")`).

**2. Assert field presence (minimum bar)**

When no explicit code is set, at least assert which field caused the error:

```python
assert "permissions" in response.data["data"]
```

**Where errors land**

| Error type | Location in `response.data["data"]` |
|------------|-------------------------------------|
| Field-level | `response.data["data"]["<field_name>"]` |
| Non-field (raised without a field key) | `response.data["data"]["GLOBAL_ERRORS"]` |

---

## Common Pitfalls

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Adding `@pytest.mark.django_db` to a base class subclass | Redundant — `BaseAPITest` already has it | Remove the decorator |
| Using `unittest.TestCase` | Breaks pytest fixtures and subtests | Use plain classes with `Test*` prefix |
| Creating instances in `_setup_base` instead of `create_instance` | Smoke tests fail because they run without valid instances | Use `create_instance()` for test data |
| Forgetting `format="json"` in POST/PATCH calls | DRF defaults to multipart, nested data breaks | Always pass `format="json"` (base classes handle this) |
| Testing business logic through API calls only | Slow, brittle, hard to isolate failures | Write unit tests for logic, integration tests for wiring |
| Putting test factories inside `apps/` | Breaks separation between production and test code | Factories always go in `tests/factories/` |

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Pure function / utility | Unit test class, no DB marker |
| Permission class logic | Unit test with mocked request |
| Full CRUD viewset | `BaseCRUDAPITest` |
| Read-only viewset | `BaseListAPITest` + `BaseRetrieveAPITest` |
| Single action (login, logout) | `BaseActionAPITest` |
| Unauthenticated endpoint | Override `_setup_base` with `api_client` |
| Custom viewset action | Separate `BaseActionAPITest` with dynamic URL |
| Serializer validation logic | Unit test calling `serializer.is_valid()` directly |
| Plugin behavior | Unit test with a minimal serializer instance |
