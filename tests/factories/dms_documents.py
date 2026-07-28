import factory

from apps.dms_documents.models import Document

from .dms_document_types import DocumentTypeFactory
from .tenants import TenantFactory


class DocumentFactory(factory.django.DjangoModelFactory):
    """Factory for creating Document test instances."""

    class Meta:
        model = Document

    tenant = factory.SubFactory(TenantFactory)
    document_type = factory.SubFactory(
        DocumentTypeFactory, tenant=factory.SelfAttribute("..tenant")
    )
    title = factory.Sequence(lambda n: f"Document {n}")
