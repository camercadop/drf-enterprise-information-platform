import factory
from django.contrib.auth.hashers import make_password

from apps.iam_mfa.models import MFABackupCode, MFADevice
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory


class MFADeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MFADevice

    tenant = factory.SubFactory(TenantFactory)
    user = factory.SubFactory(UserFactory)
    secret = factory.LazyFunction(lambda: "JBSWY3DPEHPK3PXP")  # fixed base32 for tests
    label = factory.Sequence(lambda n: f"Device {n}")
    is_active = True


class MFABackupCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MFABackupCode

    mfa_device = factory.SubFactory(MFADeviceFactory)
    code_hash = factory.LazyFunction(lambda: make_password("TESTCODE01"))
    is_used = False
