import factory

from apps.dms_document_types.models import DocumentType

from .tenants import TenantFactory


class DocumentTypeFactory(factory.django.DjangoModelFactory):
    """Factory for creating DocumentType test instances."""

    class Meta:
        model = DocumentType

    name = factory.Sequence(lambda n: f"Document Type {n}")
    description = ""
    tenant = factory.SubFactory(TenantFactory)
