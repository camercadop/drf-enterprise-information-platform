import factory

from apps.iam_teams.models import Team, TeamMembership

from .tenants import TenantFactory, TenantMembershipFactory


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: f"Team {n}")
    description = ""
    is_active = True
    tenant = factory.SubFactory(TenantFactory)


class TeamMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeamMembership

    team = factory.SubFactory(TeamFactory)
    membership = factory.SubFactory(
        TenantMembershipFactory, tenant=factory.SelfAttribute("..team.tenant")
    )
    tenant = factory.SelfAttribute("team.tenant")
