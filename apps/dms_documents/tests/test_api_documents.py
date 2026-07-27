"""Test infrastructure for DMS Documents API."""

from typing import Any

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.dms_documents.models import Document
from apps.iam_users.models import TenantMembership
from tests.base import BaseCRUDAPITest
from tests.factories.dms_document_types import DocumentTypeFactory


class TestDocumentViewSet(BaseCRUDAPITest):
    """Tests for /api/dms/documents/ CRUD."""

    url = "/api/dms/documents/"

    @pytest.fixture(autouse=True)
    def _setup_base(
        self,
        superuser_client: APIClient,
        superuser: Any,
        superuser_membership: TenantMembership,
    ) -> None:
        self.client = superuser_client
        self.user = superuser
        self.membership = superuser_membership
        self.tenant = superuser_membership.tenant

    def create_instance(self) -> Document:
        doc_type = DocumentTypeFactory(tenant=self.tenant)
        return Document.objects.create(
            tenant=self.tenant,
            document_type=doc_type,
            title="Test Document",
            owner=self.user,
            created_by=self.user,
        )

    def valid_payloads(self) -> list[dict[str, Any]]:
        return [
            {
                "title": "Annual Report",
                "description": "Company annual report",
                "document_type": DocumentTypeFactory(tenant=self.tenant).id,
            },
            {
                "title": "User Manual",
                "description": "",
                "document_type": DocumentTypeFactory(tenant=self.tenant).id,
            },
            {
                "title": "Contract",
                "description": "Legal contract",
                "document_type": None,
            },
        ]

    def invalid_payloads(
        self,
    ) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        return [
            ({"title": ""}, None),
            ({"title": "A" * 256}, None),
        ]

    def assert_instance_created(self, response: Any) -> None:
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()["data"]
        assert "id" in data
        assert "title" in data
