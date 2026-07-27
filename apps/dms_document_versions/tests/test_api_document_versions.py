"""Test infrastructure for DMS Document Versions API."""

from typing import Any

import pytest

from apps.dms_document_types.models import DocumentType
from apps.dms_document_versions.models import DocumentVersion
from apps.dms_document_versions.serializers import DocumentVersionSerializer
from apps.dms_documents.models import Document
from tests.base import BaseCreateAPITest, BaseListAPITest, BaseRetrieveAPITest
from tests.factories.dms_documents import DocumentFactory
from tests.serializer_utils import make_serializer_with_tenant_context


class TestDocumentVersionViewSet(BaseCreateAPITest, BaseRetrieveAPITest, BaseListAPITest):
    """Tests for /api/dms/documents/<document_id>/versions/ CRUD."""

    url = "/api/dms/documents/{document_id}/versions/"

    def _make_document(self) -> Document:
        type_obj, _ = DocumentType.objects.get_or_create(
            tenant=self.membership.tenant, name="Report",
            defaults={"description": "Report document"},
        )
        return Document.objects.create(
            tenant=self.membership.tenant,
            document_type=type_obj,
            title=f"Test Document {Document.objects.count()}",
        )

    def _versions_url(self, document: Document) -> str:
        return self.url.format(document_id=document.pk)

    def create_instance(self) -> DocumentVersion:
        document = self._make_document()
        return DocumentVersion.objects.create(
            tenant=self.membership.tenant,
            document=document,
            version=1,
            filename="test.pdf",
            mime_type="application/pdf",
        )

    # --- URL overrides for nested routing ---

    @property
    def _nested_url(self) -> str:
        return self._versions_url(self._make_document())

    def test_smoke_create(self) -> None:
        response = self.client.post(self._nested_url)
        assert response.status_code // 100 in (2, 4)

    def test_smoke_list(self) -> None:
        response = self.client.get(self._nested_url)
        assert response.status_code // 100 in (2, 4)

    def test_smoke_retrieve(self) -> None:
        import uuid
        response = self.client.get(f"{self._nested_url}{uuid.uuid4()}/")
        assert response.status_code // 100 in (2, 4)

    def detail_url(self, instance: DocumentVersion) -> str:
        return f"{self._versions_url(instance.document)}{instance.pk}/"

    # --- Payloads ---

    def valid_payloads(self) -> list[dict[str, Any]]:
        document = self._make_document()
        url = self._versions_url(document)
        return [
            (url, {"filename": "report_v1.pdf", "mime_type": "application/pdf"}),
            (url, {"filename": "report_v2.pdf", "mime_type": "application/pdf"}),
        ]

    def invalid_payloads(self) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        return [
            ({"filename": ""}, None),
            ({"filename": "A" * 300}, None),
        ]

    # --- Override create tests to use per-payload URLs ---

    def test_create_valid(self, subtests: Any) -> None:
        for url, payload in self.valid_payloads():
            with subtests.test(payload=payload):
                response = self.client.post(url, payload, format="json")
                assert response.status_code // 100 == 2

    def test_create_invalid(self, subtests: Any) -> None:
        url = self._nested_url
        for payload, expected_errors in self.invalid_payloads():
            with subtests.test(payload=payload):
                response = self.client.post(url, payload, format="json")
                assert response.status_code == 400

    def test_list_success(self) -> None:
        instance = self.create_instance()
        response = self.client.get(self._versions_url(instance.document))
        assert response.status_code == 200

    def test_retrieve_success(self) -> None:
        instance = self.create_instance()
        response = self.client.get(self.detail_url(instance))
        assert response.status_code == 200


@pytest.mark.django_db
class TestDocumentVersionSerializerPreCreate:
    """Unit tests for DocumentVersionSerializer.pre_create version assignment."""

    def test_first_version_is_one(self, membership: Any, user: Any) -> None:
        """Ensures version is set to 1 when no prior versions exist for the document."""
        document = DocumentFactory(tenant=membership.tenant)
        serializer = make_serializer_with_tenant_context(
            DocumentVersionSerializer,
            {"filename": "file.pdf", "mime_type": "application/pdf", "document": document.pk},
            membership,
            user,
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.version == 1

    def test_subsequent_version_increments(self, membership: Any, user: Any) -> None:
        """Ensures version increments from the last existing version."""
        document = DocumentFactory(tenant=membership.tenant)
        DocumentVersion.objects.create(
            tenant=membership.tenant, document=document, version=1, filename="v1.pdf"
        )
        serializer = make_serializer_with_tenant_context(
            DocumentVersionSerializer,
            {"filename": "file.pdf", "mime_type": "application/pdf", "document": document.pk},
            membership,
            user,
        )
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.version == 2
