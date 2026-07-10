import pytest

from apps.tenants.models import Tenant
from apps.users.models import TenantMembership, TenantRole, User
from tests.factories.tenants import (
    TenantFactory,
    TenantMembershipFactory,
    TenantRoleFactory,
)


@pytest.fixture()
def tenant() -> Tenant:
    return TenantFactory()


@pytest.fixture()
def role(tenant: Tenant) -> TenantRole:
    return TenantRoleFactory(tenant=tenant)


@pytest.fixture()
def membership(user: User, tenant: Tenant, role: TenantRole) -> TenantMembership:
    return TenantMembershipFactory(user=user, tenant=tenant, role=role)


@pytest.fixture()
def superuser_membership(
    superuser: User, tenant: Tenant, role: TenantRole
) -> TenantMembership:
    return TenantMembershipFactory(user=superuser, tenant=tenant, role=role)
