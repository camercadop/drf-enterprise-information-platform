"""Base test classes for API endpoint testing.

Provides a hierarchy of reusable test bases with automatic smoke tests
(connectivity verification), payload validation via subtests, and template
hooks for functional tests.

Hierarchy:
    BaseAPITest
    ├── BaseActionAPITest        — Non-CRUD action endpoints (login, activate, etc.)
    ├── BaseCreateAPITest        — POST create
    ├── BaseRetrieveAPITest      — GET detail
    ├── BaseListAPITest          — GET list
    ├── BaseUpdateAPITest        — PATCH/PUT update
    ├── BaseDeleteAPITest        — DELETE
    └── BaseCRUDAPITest          — All CRUD actions combined

Smoke tests verify connectivity only: the endpoint exists and doesn't crash
(response status is 2xx or 4xx). They use no payload and no valid instance.

Functional tests are provided by the base classes using template hooks:
    - valid_payloads() — list of valid data dicts for create/update
    - invalid_payloads() — list of (payload, expected_errors) tuples
    - create_instance() — factory call to produce a test object
    - update_instance() — instance for update tests (falls back to create_instance)
    - detail_url(instance) — URL for a specific resource (defaults to url + pk)
    - assert_instance_created(response) — extra checks after creation
    - assert_valid_response(response) — extra checks on retrieve
    - assert_instance_deleted(instance) — verify soft-delete state
"""

import uuid
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.iam_users.models import TenantMembership, User


@pytest.mark.django_db
class BaseAPITest:
    """Foundation for all API test classes.

    Provides an authenticated client, user, and membership via autouse fixture.
    Subclasses that test unauthenticated endpoints (e.g., login) should override
    _setup_base to use api_client instead.
    """

    @pytest.fixture(autouse=True)
    def _setup_base(
        self, auth_client: APIClient, user: User, membership: TenantMembership
    ) -> None:
        """Inject authenticated client, user, and membership into the test instance.

        Args:
            auth_client: Pre-authenticated API client.
            user: The test user.
            membership: The user's tenant membership.
        """
        self.client = auth_client
        self.user = user
        self.membership = membership


class BaseActionAPITest(BaseAPITest):
    """Base for non-CRUD action endpoints (e.g., login, logout, activate).

    Subclass must define:
        url: str — endpoint path

    Optional overrides:
        http_method: str — HTTP method (default: "post")
    """

    url: str
    http_method: str = "post"

    def test_smoke(self) -> None:
        """Verify the action endpoint is reachable and does not crash."""
        method = getattr(self.client, self.http_method)
        response = method(self.url)
        assert response.status_code // 100 in (2, 4)


class BaseCreateAPITest(BaseAPITest):
    """Base for POST create endpoints.

    Subclass must define:
        url: str — endpoint path
        valid_payloads() → list[dict] — valid creation data
        invalid_payloads() → list[tuple[dict, list | None]] — invalid data with optional error fields

    Template hooks:
        assert_instance_created(response) — extra checks after creation
    """

    url: str

    def valid_payloads(self) -> list[dict[str, Any]]:
        """Return a list of valid payloads for creation.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def invalid_payloads(self) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        """Return a list of (payload, expected_error_fields) tuples for invalid creation.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def assert_instance_created(self, response: Any) -> None:
        """Run extra assertions after a successful creation.

        Args:
            response: The successful creation response.
        """

    def test_smoke_create(self) -> None:
        """Verify the create endpoint is reachable and does not crash."""
        response = self.client.post(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_create_valid(self, subtests: Any) -> None:
        """Test creation with each valid payload succeeds.

        Args:
            subtests: Pytest subtests fixture for parameterized assertions.
        """
        for payload in self.valid_payloads():
            with subtests.test(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                assert response.status_code // 100 == 2
                self.assert_instance_created(response)

    def test_create_invalid(self, subtests: Any) -> None:
        """Test creation with each invalid payload returns 400.

        Args:
            subtests: Pytest subtests fixture for parameterized assertions.
        """
        for payload, expected_errors in self.invalid_payloads():
            with subtests.test(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                assert response.status_code == 400
                if expected_errors:
                    self._assert_error_fields(response, expected_errors)

    def _assert_error_fields(
        self, response: Any, expected_errors: list[str | dict[str, str]]
    ) -> None:
        """Assert that expected error fields or codes are present in the response.

        Args:
            response: The error response to inspect.
            expected_errors: List of field names (str) or {field: code} dicts.
        """
        data = response.data
        for error in expected_errors:
            if isinstance(error, str):
                assert error in data, f"Expected field '{error}' in response errors"
            elif isinstance(error, dict):
                for field, code in error.items():
                    assert field in data, f"Expected field '{field}' in response errors"
                    field_errors = data[field]
                    codes = [
                        getattr(e, "code", None)
                        for e in (field_errors if isinstance(field_errors, list) else [field_errors])
                    ]
                    assert code in codes, f"Expected code '{code}' for field '{field}', got {codes}"


class BaseRetrieveAPITest(BaseAPITest):
    """Base for GET detail endpoints.

    Subclass must define:
        url: str — base endpoint path
        create_instance() → object — factory call to produce a test object

    Template hooks:
        detail_url(instance) → str — URL for a specific resource
        assert_valid_response(response) — extra checks on retrieve
    """

    url: str

    def create_instance(self) -> Any:
        """Create and return a model instance for retrieval tests.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def detail_url(self, instance: Any) -> str:
        """Return the detail URL for the given instance.

        Args:
            instance: The model instance to build the URL for.

        Returns:
            The detail endpoint URL.
        """
        return f"{self.url}{instance.pk}/"

    def assert_valid_response(self, response: Any) -> None:
        """Run extra assertions on a successful retrieve response.

        Args:
            response: The successful retrieve response.
        """

    def test_smoke_retrieve(self) -> None:
        """Verify the retrieve endpoint is reachable and does not crash."""
        response = self.client.get(f"{self.url}{uuid.uuid4()}/")
        assert response.status_code // 100 in (2, 4)

    def test_retrieve_success(self) -> None:
        """Test retrieving an existing instance returns 200."""
        instance = self.create_instance()
        response = self.client.get(self.detail_url(instance))
        assert response.status_code == 200
        self.assert_valid_response(response)


class BaseListAPITest(BaseAPITest):
    """Base for GET list endpoints.

    Subclass must define:
        url: str — endpoint path
        create_instance() → object — factory call to produce test objects
    """

    url: str

    def create_instance(self) -> Any:
        """Create and return a model instance for list tests.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def test_smoke_list(self) -> None:
        """Verify the list endpoint is reachable and does not crash."""
        response = self.client.get(self.url)
        assert response.status_code // 100 in (2, 4)

    def test_list_success(self) -> None:
        """Test listing after creating an instance returns 200."""
        self.create_instance()
        response = self.client.get(self.url)
        assert response.status_code == 200


class BaseUpdateAPITest(BaseAPITest):
    """Base for PATCH/PUT update endpoints.

    Subclass must define:
        url: str — base endpoint path
        valid_payloads() → list[dict] — valid update data
        invalid_payloads() → list[tuple[dict, list | None]] — invalid data with optional error fields

    Template hooks:
        create_instance() → object — factory call (used as fallback for update_instance)
        update_instance() → object — instance for update tests
        detail_url(instance) → str — URL for a specific resource
    """

    url: str

    def create_instance(self) -> Any:
        """Create and return a model instance for update tests.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def update_instance(self) -> Any:
        """Return the instance to use for update tests.

        Defaults to create_instance(). Override for custom setup.
        """
        return self.create_instance()

    def detail_url(self, instance: Any) -> str:
        """Return the detail URL for the given instance.

        Args:
            instance: The model instance to build the URL for.

        Returns:
            The detail endpoint URL.
        """
        return f"{self.url}{instance.pk}/"

    def valid_payloads(self) -> list[dict[str, Any]]:
        """Return a list of valid payloads for update.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def invalid_payloads(self) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        """Return a list of (payload, expected_error_fields) tuples for invalid update.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def test_smoke_update(self) -> None:
        """Verify the update endpoint is reachable and does not crash."""
        response = self.client.patch(f"{self.url}{uuid.uuid4()}/")
        assert response.status_code // 100 in (2, 4)

    def test_update_valid(self, subtests: Any) -> None:
        """Test update with each valid payload succeeds.

        Args:
            subtests: Pytest subtests fixture for parameterized assertions.
        """
        instance = self.update_instance()
        for payload in self.valid_payloads():
            with subtests.test(payload=payload):
                response = self.client.patch(
                    self.detail_url(instance), payload, format="json"
                )
                assert response.status_code // 100 == 2

    def test_update_invalid(self, subtests: Any) -> None:
        """Test update with each invalid payload returns 400.

        Args:
            subtests: Pytest subtests fixture for parameterized assertions.
        """
        instance = self.update_instance()
        for payload, expected_errors in self.invalid_payloads():
            with subtests.test(payload=payload):
                response = self.client.patch(
                    self.detail_url(instance), payload, format="json"
                )
                assert response.status_code == 400
                if expected_errors:
                    self._assert_error_fields(response, expected_errors)

    def _assert_error_fields(
        self, response: Any, expected_errors: list[str | dict[str, str]]
    ) -> None:
        """Assert that expected error fields or codes are present in the response.

        Args:
            response: The error response to inspect.
            expected_errors: List of field names (str) or {field: code} dicts.
        """
        data = response.data
        for error in expected_errors:
            if isinstance(error, str):
                assert error in data, f"Expected field '{error}' in response errors"
            elif isinstance(error, dict):
                for field, code in error.items():
                    assert field in data, f"Expected field '{field}' in response errors"
                    field_errors = data[field]
                    codes = [
                        getattr(e, "code", None)
                        for e in (field_errors if isinstance(field_errors, list) else [field_errors])
                    ]
                    assert code in codes, f"Expected code '{code}' for field '{field}', got {codes}"


class BaseDeleteAPITest(BaseAPITest):
    """Base for DELETE endpoints.

    Subclass must define:
        url: str — base endpoint path
        create_instance() → object — factory call to produce a test object

    Template hooks:
        detail_url(instance) → str — URL for a specific resource
        assert_instance_deleted(instance) — verify soft-delete state
    """

    url: str

    def create_instance(self) -> Any:
        """Create and return a model instance for deletion tests.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    def detail_url(self, instance: Any) -> str:
        """Return the detail URL for the given instance.

        Args:
            instance: The model instance to build the URL for.

        Returns:
            The detail endpoint URL.
        """
        return f"{self.url}{instance.pk}/"

    def assert_instance_deleted(self, instance: Any) -> None:
        """Verify the instance was soft-deleted.

        Args:
            instance: The model instance to check.
        """
        instance.refresh_from_db()
        assert instance.deleted_at is not None

    def test_smoke_delete(self) -> None:
        """Verify the delete endpoint is reachable and does not crash."""
        response = self.client.delete(f"{self.url}{uuid.uuid4()}/")
        assert response.status_code // 100 in (2, 4)

    def test_delete_success(self) -> None:
        """Test deleting an existing instance returns 204 and soft-deletes it."""
        instance = self.create_instance()
        response = self.client.delete(self.detail_url(instance))
        assert response.status_code == 204
        self.assert_instance_deleted(instance)


class BaseCRUDAPITest(
    BaseCreateAPITest,
    BaseRetrieveAPITest,
    BaseListAPITest,
    BaseUpdateAPITest,
    BaseDeleteAPITest,
):
    """Base for full CRUD viewsets.

    Combines all CRUD smoke tests and functional tests. Use individual bases
    if the viewset only supports a subset of actions.

    Subclass must define:
        url: str — base endpoint path
        valid_payloads() → list[dict]
        invalid_payloads() → list[tuple[dict, list | None]]
        create_instance() → object
    """
