import factory

from apps.iam_roles.models import TenantRole
from apps.iam_users.models import TenantMembership
from apps.tenants.models import Tenant

from .users import UserFactory


class TenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tenant

    name = factory.Sequence(lambda n: f"Tenant {n}")
    code = factory.Sequence(lambda n: f"tenant-{n}")
    is_active = True


class TenantRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TenantRole
        django_get_or_create = ("tenant", "name")

    name = "Member"
    kind = "member"
    tenant = factory.SubFactory(TenantFactory)


class TenantMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TenantMembership

    user = factory.SubFactory(UserFactory)
    tenant = factory.SubFactory(TenantFactory)
    role = factory.SubFactory(TenantRoleFactory, tenant=factory.SelfAttribute("..tenant"))
    is_admin = False
    is_active = True
