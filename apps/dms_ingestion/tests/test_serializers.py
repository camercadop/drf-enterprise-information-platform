"""Unit tests for dms_ingestion serializers."""

import pytest

from apps.dms_ingestion.serializers import UploadSessionCreateSerializer
from tests.factories.dms_document_types import DocumentTypeFactory
from tests.serializer_utils import make_serializer_with_tenant_context


@pytest.mark.django_db
class TestUploadSessionCreateSerializerValidateDocumentType:
    def _base_payload(self, **kwargs) -> dict:  # type: ignore[type-arg]
        return {
            "title": "My Document",
            "filename": "file.pdf",
            "mime_type": "application/pdf",
            "size": 1024,
            **kwargs,
        }

    def test_valid_document_type_returns_canonical_name(self, membership, user) -> None:
        doc_type = DocumentTypeFactory(tenant=membership.tenant, name="Invoice")
        serializer = make_serializer_with_tenant_context(
            UploadSessionCreateSerializer,
            self._base_payload(document_type="invoice"),
            membership,
            user,
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["document_type"] == doc_type.name

    def test_valid_without_document_type(self, membership, user) -> None:
        serializer = make_serializer_with_tenant_context(
            UploadSessionCreateSerializer,
            self._base_payload(),
            membership,
            user,
        )
        assert serializer.is_valid(), serializer.errors

    def test_invalid_document_type_not_found(self, membership, user) -> None:
        serializer = make_serializer_with_tenant_context(
            UploadSessionCreateSerializer,
            self._base_payload(document_type="NonExistent"),
            membership,
            user,
        )
        assert not serializer.is_valid()
        assert "document_type" in serializer.errors

    def test_document_type_scoped_to_tenant(self, membership, user) -> None:
        DocumentTypeFactory(name="Contract")  # different tenant
        serializer = make_serializer_with_tenant_context(
            UploadSessionCreateSerializer,
            self._base_payload(document_type="Contract"),
            membership,
            user,
        )
        assert not serializer.is_valid()
        assert "document_type" in serializer.errors
