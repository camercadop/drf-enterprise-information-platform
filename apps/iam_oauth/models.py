from django.db import models

from apps.tenants.models import TenantAwareModel


class OAuth2Client(TenantAwareModel):
    """Registered OAuth2 client application belonging to a tenant."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="oauth2_clients",
        db_index=True,
    )
    # The tenant this client belongs to

    client_id = models.CharField(max_length=255)
    # Unique identifier for the OAuth2 client

    client_secret = models.CharField(max_length=255, null=True, blank=True)
    # Client secret for confidential clients; null for public clients

    client_name = models.CharField(max_length=255)
    # Human-readable name of the client application

    redirect_uris = models.TextField()
    # Comma-separated list of allowed redirect URIs

    grant_types = models.TextField()
    # Comma-separated list of allowed grant types

    response_types = models.TextField()
    # Comma-separated list of allowed response types

    scope = models.TextField(default="")
    # Space-separated list of allowed scopes

    is_confidential = models.BooleanField(default=True)
    # Whether the client is a confidential client (can hold a secret)

    is_active = models.BooleanField(default=True)
    # Whether the client is currently active

    class Meta:
        db_table = "iam_oauth_clients"
        ordering = ["client_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "client_id"],
                name="unique_client_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.client_name} ({self.client_id})"

    @property
    def redirect_uri_list(self) -> list[str]:
        return [uri.strip() for uri in self.redirect_uris.split(",") if uri.strip()]

    @property
    def grant_type_list(self) -> list[str]:
        return [g.strip() for g in self.grant_types.split(",") if g.strip()]

    @property
    def response_type_list(self) -> list[str]:
        return [r.strip() for r in self.response_types.split(",") if r.strip()]

    @property
    def scope_list(self) -> list[str]:
        return [s.strip() for s in self.scope.split() if s.strip()]


class AuthorizationCode(TenantAwareModel):
    """Authorization code for the OAuth2 Authorization Code flow.

    Issued during the /authorize endpoint and consumed at the /token
    endpoint. Codes are single-use and expire after a short lifetime.
    """

    client = models.ForeignKey(
        OAuth2Client,
        on_delete=models.CASCADE,
        related_name="authorization_codes",
        db_index=True,
    )
    # The client that requested this authorization code

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="authorization_codes",
        db_index=True,
    )
    # The tenant context for this authorization code

    code = models.CharField(max_length=255)
    # The authorization code value

    redirect_uri = models.URLField(max_length=2048)
    # The redirect URI that was used in the authorization request

    scope = models.TextField(default="")
    # Space-separated list of scopes granted in this authorization

    code_challenge = models.CharField(max_length=255, null=True, blank=True)
    # PKCE code challenge for public clients

    code_challenge_method = models.CharField(max_length=10, null=True, blank=True)
    # PKCE code challenge method (e.g., "S256")

    user_id = models.UUIDField(null=True, blank=True)
    # The user who authorized this code

    expires_at = models.DateTimeField()
    # Timestamp when this code expires; codes are single-use and short-lived

    is_consumed = models.BooleanField(default=False)
    # Whether this code has already been consumed

    consumed_at = models.DateTimeField(null=True, blank=True)
    # Timestamp when this code was consumed

    class Meta:
        db_table = "iam_oauth_authorization_codes"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "code"],
                name="unique_auth_code_per_client",
            ),
        ]
        indexes = [
            models.Index(
                fields=["code"],
                name="idx_auth_code_code",
            ),
            models.Index(
                fields=["client", "is_consumed"],
                name="idx_auth_code_client_consumed",
            ),
        ]

    def __str__(self) -> str:
        return f"AuthCode({self.code[:8]}...) for {self.client.client_id}"


class OAuth2RefreshToken(TenantAwareModel):
    """Refresh token issued as part of the OAuth2 Authorization Code flow.

    Tracks issued refresh tokens to support rotation and revocation.
    Each rotation creates a new record and links it via replaced_by.
    """

    client = models.ForeignKey(
        OAuth2Client,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
        db_index=True,
    )
    # The client this refresh token was issued to

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="oauth2_refresh_tokens",
        db_index=True,
    )
    # The tenant context for this refresh token

    user_id = models.UUIDField()
    # The user this refresh token was issued for

    token = models.CharField(max_length=255, unique=True)
    # Opaque token reference stored in the JWT jti claim

    scope = models.TextField(default="")
    # Space-separated list of scopes granted to this token

    expires_at = models.DateTimeField()
    # Timestamp when this refresh token expires

    is_revoked = models.BooleanField(default=False)
    # Whether this token has been explicitly revoked

    revoked_at = models.DateTimeField(null=True, blank=True)
    # Timestamp when this token was revoked

    replaced_by = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
    )
    # The new refresh token that replaced this one after rotation

    class Meta:
        db_table = "iam_oauth_refresh_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"], name="idx_oauth_refresh_token_token"),
            models.Index(
                fields=["client", "is_revoked"], name="idx_oauth_rt_client_revoked"
            ),
            models.Index(
                fields=["user_id", "is_revoked"], name="idx_oauth_rt_user_revoked"
            ),
        ]

    def __str__(self) -> str:
        return f"OAuth2RefreshToken({self.token[:8]}...) for {self.client.client_id}"
