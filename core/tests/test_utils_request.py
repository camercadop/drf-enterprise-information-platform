"""Tests for core.utils.request module."""

from unittest.mock import MagicMock, patch

from core.utils.request import get_client_ip, get_request_data


class TestGetClientIp:
    def test_returns_ip_when_available(self) -> None:
        request = MagicMock()
        with patch("core.utils.request._get_client_ip", return_value=("192.168.1.1", True)):
            result = get_client_ip(request)
        assert result == "192.168.1.1"

    def test_returns_empty_string_when_none(self) -> None:
        request = MagicMock()
        with patch("core.utils.request._get_client_ip", return_value=(None, False)):
            result = get_client_ip(request)
        assert result == ""


class TestGetRequestData:
    def test_json_content_type(self) -> None:
        request = MagicMock()
        request.content_type = "application/json"
        request.data = {"key": "value"}
        result = get_request_data(request)
        assert result == {"key": "value"}

    def test_form_urlencoded_content_type(self) -> None:
        request = MagicMock()
        request.content_type = "application/x-www-form-urlencoded"
        request.POST.dict.return_value = {"field": "data"}
        result = get_request_data(request)
        assert result == {"field": "data"}

    def test_multipart_form_data_content_type(self) -> None:
        request = MagicMock()
        request.content_type = "multipart/form-data; boundary=----"
        request.POST.dict.return_value = {"file_field": "name"}
        result = get_request_data(request)
        assert result == {"file_field": "name"}

    def test_unknown_content_type_returns_empty_dict(self) -> None:
        request = MagicMock()
        request.content_type = "text/plain"
        result = get_request_data(request)
        assert result == {}
