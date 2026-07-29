import factory

from apps.iam_oauth.models import AuthorizationCode, OAuth2Client, OAuth2RefreshToken
from tests.factories.tenants import TenantFactory
from tests.factories.users import UserFactory


class OAuth2ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OAuth2Client

    tenant = factory.SubFactory(TenantFactory)
    client_id = factory.Sequence(lambda n: f"client-{n}")
    client_secret = factory.Sequence(lambda n: f"secret-{n}")
    client_name = factory.Sequence(lambda n: f"Client {n}")
    redirect_uris = "https://example.com/callback"
    grant_types = "authorization_code,refresh_token"
    response_types = "code"
    scope = "read write"
    is_confidential = True
    is_active = True


class PublicOAuth2ClientFactory(OAuth2ClientFactory):
    is_confidential = False
    client_secret = None
    grant_types = "authorization_code"


class AuthorizationCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthorizationCode

    client = factory.SubFactory(OAuth2ClientFactory)
    tenant = factory.SelfAttribute("client.tenant")
    code = factory.Sequence(lambda n: f"code{n:032d}")
    redirect_uri = "https://example.com/callback"
    scope = "read write"
    user_id = factory.LazyFunction(lambda: UserFactory().pk)
    expires_at = factory.LazyFunction(
        lambda: __import__("django.utils.timezone", fromlist=["now"]).now()
        + __import__("datetime").timedelta(seconds=600)
    )


class OAuth2RefreshTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OAuth2RefreshToken

    client = factory.SubFactory(OAuth2ClientFactory)
    tenant = factory.SelfAttribute("client.tenant")
    user_id = factory.LazyFunction(lambda: UserFactory().pk)
    token = factory.Sequence(lambda n: f"token{n:032d}")
    scope = "read write"
    expires_at = factory.LazyFunction(
        lambda: __import__("django.utils.timezone", fromlist=["now"]).now()
        + __import__("datetime").timedelta(days=7)
    )
