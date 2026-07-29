"""Tests for dms_documents event handlers."""

import pytest

from apps.dms_document_versions.models import DocumentVersion
from apps.dms_documents.event_handlers import handle_document_created
from apps.dms_documents.models import Document
from apps.sys_eventbus.envelope import EventEnvelope
from tests.factories.dms_document_types import DocumentTypeFactory
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory


def _make_envelope(tenant_id: str, actor_id: str, **payload_overrides: object) -> EventEnvelope:
    payload = {
        "session_id": "session-1",
        "title": "Annual Report",
        "document_type": None,
        "filename": "report.pdf",
        "mime_type": "application/pdf",
        "size": 1024,
        "checksum": "abc123",
        "extension": ".pdf",
        "storage_key": "session-1/report.pdf",
        **payload_overrides,
    }
    return EventEnvelope(
        type="document.created",
        payload=payload,
        tenant_id=tenant_id,
        actor_id=actor_id,
    )


@pytest.mark.django_db
class TestHandleDocumentCreated:
    def test_creates_document_and_version(self) -> None:
        tenant = TenantFactory()
        user = UserFactory()
        envelope = _make_envelope(str(tenant.id), str(user.id))

        handle_document_created(envelope)

        assert Document.objects.filter(tenant=tenant, title="Annual Report").exists()
        doc = Document.objects.get(tenant=tenant, title="Annual Report")
        assert DocumentVersion.objects.filter(document=doc, version=1).exists()

    def test_resolves_document_type_id(self) -> None:
        tenant = TenantFactory()
        user = UserFactory()
        doc_type = DocumentTypeFactory(tenant=tenant, name="Invoice")
        envelope = _make_envelope(str(tenant.id), str(user.id), document_type="invoice")

        handle_document_created(envelope)

        doc = Document.objects.get(tenant=tenant)
        assert doc.document_type_id == doc_type.id

    def test_raises_when_document_type_not_found(self) -> None:
        tenant = TenantFactory()
        user = UserFactory()
        envelope = _make_envelope(str(tenant.id), str(user.id), document_type="NonExistent")

        with pytest.raises(ValueError, match="NonExistent"):
            handle_document_created(envelope)

        assert not Document.objects.filter(tenant=tenant).exists()

    def test_document_type_not_resolved_across_tenants(self) -> None:
        tenant = TenantFactory()
        other_tenant = TenantFactory()
        user = UserFactory()
        DocumentTypeFactory(tenant=other_tenant, name="Contract")
        envelope = _make_envelope(str(tenant.id), str(user.id), document_type="Contract")

        with pytest.raises(ValueError, match="Contract"):
            handle_document_created(envelope)

    def test_creates_document_without_document_type(self) -> None:
        tenant = TenantFactory()
        user = UserFactory()
        envelope = _make_envelope(str(tenant.id), str(user.id), document_type=None)

        handle_document_created(envelope)

        doc = Document.objects.get(tenant=tenant)
        assert doc.document_type_id is None
