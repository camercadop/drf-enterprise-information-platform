"""Integration tests for health check endpoints."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client() -> APIClient:
    """Unauthenticated API client for health endpoints."""
    return APIClient()


class TestLiveness:
    """Tests for GET /health/live/."""

    url = "/health/live/"

    def test_returns_200(self, client: APIClient) -> None:
        """Liveness probe returns 200 unconditionally."""
        response = client.get(self.url)
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


@pytest.mark.django_db
class TestReadiness:
    """Tests for GET /health/ready/."""

    url = "/health/ready/"

    def test_returns_200_when_healthy(self, client: APIClient) -> None:
        """Readiness probe returns 200 when DB and cache are reachable."""
        response = client.get(self.url)
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_returns_503_when_database_unavailable(self, client: APIClient) -> None:
        """Readiness probe returns 503 when database connection fails."""
        with patch(
            "django.db.connection.ensure_connection",
            side_effect=Exception("connection refused"),
        ):
            response = client.get(self.url)

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert "database" in data["errors"]

    def test_returns_503_when_cache_unavailable(self, client: APIClient) -> None:
        """Readiness probe returns 503 when cache is unreachable."""
        with patch(
            "django.core.cache.cache.set",
            side_effect=Exception("redis timeout"),
        ):
            response = client.get(self.url)

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert "cache" in data["errors"]

    def test_returns_503_when_cache_readback_fails(self, client: APIClient) -> None:
        """Readiness probe returns 503 when cache read-back mismatches."""
        with patch("django.core.cache.cache.get", return_value="wrong"):
            response = client.get(self.url)

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["errors"]["cache"] == "read-back mismatch"
