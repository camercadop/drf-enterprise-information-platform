"""Integration tests for DMS Metadata Definitions API."""

import uuid
from typing import Any

import pytest

from apps.dms_document_types.models import DocumentType
from apps.dms_metadata.models import MetadataDefinition
from apps.dms_metadata.metadata_types import MetadataType
from tests.base import (
    BaseCreateAPITest,
    BaseDeleteAPITest,
    BaseListAPITest,
    BaseRetrieveAPITest,
    BaseUpdateAPITest,
)
from tests.factories.dms_metadata import MetadataDefinitionFactory


class TestMetadataDefinitionViewSet(
    BaseCreateAPITest,
    BaseRetrieveAPITest,
    BaseListAPITest,
    BaseUpdateAPITest,
    BaseDeleteAPITest,
):
    """Tests for /api/dms/document-types/<id>/metadata-definitions/ CRUD."""

    url = "/api/dms/document-types/{document_type_id}/metadata-definitions/"

    def _make_document_type(self) -> DocumentType:
        doc_type, _ = DocumentType.objects.get_or_create(
            tenant=self.membership.tenant,
            name=f"Type {DocumentType.objects.count()}",
        )
        return doc_type

    def _nested_url(self, document_type: DocumentType) -> str:
        return self.url.format(document_type_id=document_type.pk)

    def create_instance(self) -> MetadataDefinition:
        return MetadataDefinitionFactory(
            tenant=self.membership.tenant,
            document_type=self._make_document_type(),
        )

    def detail_url(self, instance: MetadataDefinition) -> str:
        return f"{self._nested_url(instance.document_type)}{instance.pk}/"

    # --- Smoke test overrides for nested routing ---

    def test_smoke_create(self) -> None:
        response = self.client.post(self._nested_url(self._make_document_type()))
        assert response.status_code // 100 in (2, 4)

    def test_smoke_list(self) -> None:
        response = self.client.get(self._nested_url(self._make_document_type()))
        assert response.status_code // 100 in (2, 4)

    def test_smoke_retrieve(self) -> None:
        response = self.client.get(
            f"{self._nested_url(self._make_document_type())}{uuid.uuid4()}/"
        )
        assert response.status_code // 100 in (2, 4)

    def test_smoke_update(self) -> None:
        response = self.client.patch(
            f"{self._nested_url(self._make_document_type())}{uuid.uuid4()}/"
        )
        assert response.status_code // 100 in (2, 4)

    def test_smoke_delete(self) -> None:
        response = self.client.delete(
            f"{self._nested_url(self._make_document_type())}{uuid.uuid4()}/"
        )
        assert response.status_code // 100 in (2, 4)

    # --- Payloads ---

    def valid_payloads(self) -> list[Any]:
        doc_type = self._make_document_type()
        url = self._nested_url(doc_type)
        return [
            (url, {"code": "invoice_number", "name": "Invoice Number", "data_type": MetadataType.STRING}),
            (url, {"code": "amount", "name": "Amount", "data_type": MetadataType.DECIMAL, "required": True}),
            (
                url,
                {
                    "code": "currency",
                    "name": "Currency",
                    "data_type": MetadataType.ENUM,
                    "validation_rules": {"choices": ["USD", "EUR", "COP"]},
                    "default_value": "USD",
                },
            ),
        ]

    def invalid_payloads(self) -> list[tuple[dict[str, Any], list[str | dict[str, str]] | None]]:
        return [
            ({"code": ""}, ["code"]),
            ({"code": "x", "name": "X", "data_type": "INVALID_TYPE"}, ["data_type"]),
            (
                {"code": "x", "name": "X", "data_type": MetadataType.STRING, "validation_rules": {"min_length": "not-an-int"}},
                ["validation_rules"],
            ),
            (
                {"code": "x", "name": "X", "data_type": MetadataType.INTEGER, "default_value": "not-an-int"},
                ["default_value"],
            ),
        ]

    # --- Override create/update tests for nested URL pattern ---

    def test_create_valid(self, subtests: Any) -> None:
        for url, payload in self.valid_payloads():
            with subtests.test(payload=payload):
                response = self.client.post(url, payload, format="json")
                assert response.status_code // 100 == 2

    def test_create_invalid(self, subtests: Any) -> None:
        url = self._nested_url(self._make_document_type())
        create_invalid = [
            ({}, ["code", "name", "data_type"]),
        ] + self.invalid_payloads()
        for payload, expected_errors in create_invalid:
            with subtests.test(payload=payload):
                response = self.client.post(url, payload, format="json")
                assert response.status_code == 400
                if expected_errors:
                    self._assert_error_fields(response, expected_errors)

    def test_update_valid(self, subtests: Any) -> None:
        instance = self.create_instance()
        for _, payload in self.valid_payloads():
            with subtests.test(payload=payload):
                response = self.client.patch(self.detail_url(instance), payload, format="json")
                assert response.status_code // 100 == 2

    def test_update_invalid(self, subtests: Any) -> None:
        instance = self.create_instance()
        for payload, expected_errors in self.invalid_payloads():
            with subtests.test(payload=payload):
                response = self.client.patch(self.detail_url(instance), payload, format="json")
                assert response.status_code == 400
                if expected_errors:
                    self._assert_error_fields(response, expected_errors)

    def test_list_success(self) -> None:
        instance = self.create_instance()
        response = self.client.get(self._nested_url(instance.document_type))
        assert response.status_code == 200

    def test_retrieve_success(self) -> None:
        instance = self.create_instance()
        response = self.client.get(self.detail_url(instance))
        assert response.status_code == 200

    def test_delete_success(self) -> None:
        instance = self.create_instance()
        response = self.client.delete(self.detail_url(instance))
        assert response.status_code == 204
        instance.refresh_from_db()
        assert instance.deleted_at is not None


@pytest.mark.django_db
class TestMetadataDefinitionUniqueness:
    """Tests for the unique constraint on (tenant, document_type, code)."""

    def test_duplicate_code_same_document_type_rejected(self, membership: Any, auth_client: Any) -> None:
        doc_type, _ = DocumentType.objects.get_or_create(
            tenant=membership.tenant, name="Invoice"
        )
        MetadataDefinitionFactory(
            tenant=membership.tenant, document_type=doc_type, code="ref"
        )
        url = f"/api/dms/document-types/{doc_type.pk}/metadata-definitions/"
        response = auth_client.post(
            url,
            {"code": "ref", "name": "Reference", "data_type": MetadataType.STRING},
            format="json",
        )
        assert response.status_code == 400

    def test_same_code_different_document_type_allowed(self, membership: Any, auth_client: Any) -> None:
        doc_type_a, _ = DocumentType.objects.get_or_create(
            tenant=membership.tenant, name="Invoice"
        )
        doc_type_b, _ = DocumentType.objects.get_or_create(
            tenant=membership.tenant, name="Contract"
        )
        MetadataDefinitionFactory(
            tenant=membership.tenant, document_type=doc_type_a, code="ref"
        )
        url = f"/api/dms/document-types/{doc_type_b.pk}/metadata-definitions/"
        response = auth_client.post(
            url,
            {"code": "ref", "name": "Reference", "data_type": MetadataType.STRING},
            format="json",
        )
        assert response.status_code // 100 == 2
