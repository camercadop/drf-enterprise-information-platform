import factory

from apps.dms_metadata.metadata_types import MetadataType
from apps.dms_metadata.models import MetadataDefinition

from .dms_document_types import DocumentTypeFactory
from .tenants import TenantFactory


class MetadataDefinitionFactory(factory.django.DjangoModelFactory):
    """Factory for creating MetadataDefinition test instances."""

    class Meta:
        model = MetadataDefinition

    tenant = factory.SubFactory(TenantFactory)
    document_type = factory.SubFactory(
        DocumentTypeFactory, tenant=factory.SelfAttribute("..tenant")
    )
    code = factory.Sequence(lambda n: f"field_{n}")
    name = factory.Sequence(lambda n: f"Field {n}")
    data_type = MetadataType.STRING
    required = False
