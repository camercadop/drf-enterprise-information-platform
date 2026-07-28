import factory

from apps.dms_ingestion.models import UploadSession

from .tenants import TenantFactory
from .users import UserFactory


class UploadSessionFactory(factory.django.DjangoModelFactory):
    """Factory for creating UploadSession test instances."""

    class Meta:
        model = UploadSession

    tenant = factory.SubFactory(TenantFactory)
    created_by = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Upload Session {n}")
    filename = factory.Sequence(lambda n: f"file_{n}.pdf")
    mime_type = "application/pdf"
    size = 1024
    state = UploadSession.State.NEW
