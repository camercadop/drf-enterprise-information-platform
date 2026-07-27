"""Shared utilities for serializer unit tests."""

from typing import Any

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.iam_users.models import TenantMembership, User


def make_serializer_with_tenant_context(
    serializer_class: type[serializers.Serializer],
    data: dict[str, Any],
    membership: TenantMembership,
    user: User,
) -> serializers.Serializer:
    """Instantiate a serializer with a mock request carrying tenant and user context.

    Use this in unit tests that call serializer.save() directly, bypassing the
    API layer, when the serializer relies on global plugins that read tenant_id
    from JWT claims (TenantInjectionSerializerPlugin) or request.user (audit plugin).

    Args:
        serializer_class: The serializer class to instantiate.
        data: The input data dict to validate.
        membership: The tenant membership providing the tenant context.
        user: The user to attach to the mock request.

    Returns:
        An unvalidated serializer instance ready for is_valid() / save().
    """
    factory = APIRequestFactory()
    request = Request(factory.get("/"))
    request.auth = {"tenant_id": str(membership.tenant.pk)}  # type: ignore[assignment]
    request.user = user
    return serializer_class(data=data, context={"request": request})
