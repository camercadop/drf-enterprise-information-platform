"""
Test that unauthenticated requests are rejected globally by default.

This single test validates ADR-003 compliance: all endpoints inheriting from
the base viewset require authentication unless explicitly opted out.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestDefaultAuthenticationEnforcement:
    """Verify that the global IsAuthenticated default rejects anonymous requests."""

    def test_unauthenticated_request_returns_401(self) -> None:
        client = APIClient()
        response = client.get("/api/tenants/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
