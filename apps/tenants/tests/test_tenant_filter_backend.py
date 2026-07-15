"""Tests for TenantFilterBackend."""

from unittest.mock import MagicMock

import pytest

from apps.tenants.filters import TenantFilterBackend
from apps.tenants.models import Team, Tenant
from apps.iam_users.models import TenantMembership
from tests.factories.tenants import (
    TenantFactory,
    TenantMembershipFactory,
    TenantRoleFactory,
)


@pytest.mark.django_db
class TestTenantFilterBackend:
    """Tests for automatic tenant-scoped queryset filtering."""

    @pytest.fixture()
    def backend(self) -> TenantFilterBackend:
        return TenantFilterBackend()

    @pytest.fixture()
    def tenant_a(self) -> Tenant:
        return TenantFactory()

    @pytest.fixture()
    def tenant_b(self) -> Tenant:
        return TenantFactory()

    @pytest.fixture()
    def team_a(self, tenant_a: Tenant) -> Team:
        return Team.objects.create(tenant=tenant_a, name="Team A")

    @pytest.fixture()
    def team_b(self, tenant_b: Tenant) -> Team:
        return Team.objects.create(tenant=tenant_b, name="Team B")

    def _make_request(self, tenant_id: str | None = None) -> MagicMock:
        request = MagicMock()
        if tenant_id:
            request.auth = {"tenant_id": tenant_id}
        else:
            request.auth = None
        return request

    def _make_view(self, tenant_scoping: bool = True) -> MagicMock:
        view = MagicMock()
        view.tenant_scoping = tenant_scoping
        return view

    def test_filters_queryset_by_tenant_id(
        self, backend: TenantFilterBackend, tenant_a: Tenant, team_a: Team, team_b: Team
    ) -> None:
        """Returns only records matching the JWT tenant_id."""
        request = self._make_request(tenant_id=str(tenant_a.pk))
        view = self._make_view()
        qs = backend.filter_queryset(request, Team.objects.all(), view)
        assert list(qs) == [team_a]

    def test_returns_empty_when_no_tenant_claim(
        self, backend: TenantFilterBackend, team_a: Team
    ) -> None:
        """Returns empty queryset when request has no tenant_id claim."""
        request = self._make_request(tenant_id=None)
        view = self._make_view()
        qs = backend.filter_queryset(request, Team.objects.all(), view)
        assert qs.count() == 0

    def test_noop_when_model_has_no_tenant_field(
        self, backend: TenantFilterBackend, tenant_a: Tenant
    ) -> None:
        """Does not filter models without a tenant_id field."""
        request = self._make_request(tenant_id=str(tenant_a.pk))
        view = self._make_view()
        qs = backend.filter_queryset(request, Tenant.objects.all(), view)
        assert tenant_a in qs

    def test_noop_when_tenant_scoping_false(
        self, backend: TenantFilterBackend, tenant_a: Tenant, team_a: Team, team_b: Team
    ) -> None:
        """Does not filter when view sets tenant_scoping = False."""
        request = self._make_request(tenant_id=str(tenant_a.pk))
        view = self._make_view(tenant_scoping=False)
        qs = backend.filter_queryset(request, Team.objects.all(), view)
        assert team_a in qs
        assert team_b in qs

    def test_filters_memberships_by_tenant(
        self, backend: TenantFilterBackend, tenant_a: Tenant, tenant_b: Tenant
    ) -> None:
        """Filters TenantMembership records by tenant_id from JWT."""
        role_a = TenantRoleFactory(tenant=tenant_a)
        role_b = TenantRoleFactory(tenant=tenant_b)
        membership_a = TenantMembershipFactory(tenant=tenant_a, role=role_a)
        membership_b = TenantMembershipFactory(tenant=tenant_b, role=role_b)

        request = self._make_request(tenant_id=str(tenant_a.pk))
        view = self._make_view()
        qs = backend.filter_queryset(request, TenantMembership.objects.all(), view)
        assert membership_a in qs
        assert membership_b not in qs

    def test_empty_queryset_when_auth_has_no_get(
        self, backend: TenantFilterBackend, team_a: Team
    ) -> None:
        """Returns empty queryset when auth object has no get method."""
        request = MagicMock()
        request.auth = object()
        view = self._make_view()
        qs = backend.filter_queryset(request, Team.objects.all(), view)
        assert qs.count() == 0
