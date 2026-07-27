"""Tests for DocumentType CRUD endpoints."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.dms_document_types.models import DocumentType
from apps.iam_users.models import TenantMembership
from tests.base import BaseCRUDAPITest
from tests.factories.dms_document_types import DocumentTypeFactory

URL = "/api/dms/document-types/"


class TestDocumentTypeViewSet(BaseCRUDAPITest):
    """Tests for /api/dms/document-types/ CRUD."""

    url = "/api/dms/document-types/"

    @pytest.fixture(autouse=True)
    def _setup_base(
        self,
        superuser_client: APIClient,
        superuser: Any,
        superuser_membership: TenantMembership,
    ) -> None:
        # DocumentType write endpoints require tenant membership
        # (write operations don't require special permissions in this module)
        self.client = superuser_client
        self.user = superuser
        self.membership = superuser_membership

    def create_instance(self) -> DocumentType:
        """Create a document type in the test tenant."""
        return DocumentTypeFactory(
            tenant=self.membership.tenant, name="Test Document"
        )

    def valid_payloads(self) -> list[dict[str, Any]]:
        """Return valid document type creation payloads."""
        return [
            {"name": "Report", "description": "Report document"},
            {"name": "Summary", "description": ""},
            {"name": "Contract", "description": "Contract document"},
        ]

    def invalid_payloads(
        self,
    ) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        """Return invalid payloads that should fail."""
        return [
            ({"name": ""}, None),
            ({"name": "A" * 101}, None),  # Exceeds max_length=100
        ]

    def assert_instance_created(self, response) -> None:
        """Run extra assertions after a successful creation."""
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()["data"]
        assert "name" in data
        assert "id" in data
        assert data["name"] in [
            "Report",
            "Summary",
            "Contract",
        ]