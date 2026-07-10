from unittest.mock import MagicMock

from apps.tenants.utils import get_tenant_id


class TestGetTenantId:
    def test_extracts_tenant_id_from_auth(self) -> None:
        request = MagicMock()
        request.auth = {"tenant_id": "abc-123"}
        assert get_tenant_id(request) == "abc-123"

    def test_returns_none_when_no_auth(self) -> None:
        request = MagicMock()
        request.auth = None
        assert get_tenant_id(request) is None

    def test_returns_none_when_auth_has_no_get(self) -> None:
        request = MagicMock()
        request.auth = object()
        assert get_tenant_id(request) is None

    def test_returns_none_when_tenant_id_missing(self) -> None:
        request = MagicMock()
        request.auth = {"other_key": "value"}
        assert get_tenant_id(request) is None
