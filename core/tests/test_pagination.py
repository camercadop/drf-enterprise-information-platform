from unittest.mock import MagicMock

from core.pagination.page import CustomPagination


class TestCustomPaginationGetPageSize:
    def setup_method(self) -> None:
        self.pagination = CustomPagination()

    def test_returns_default_when_no_param(self) -> None:
        request = MagicMock()
        request.query_params = {}
        assert self.pagination.get_page_size(request) == 10

    def test_returns_requested_size(self) -> None:
        request = MagicMock()
        request.query_params = {"page_size": "25"}
        assert self.pagination.get_page_size(request) == 25

    def test_caps_at_max_page_size(self) -> None:
        request = MagicMock()
        request.query_params = {"page_size": "999"}
        assert self.pagination.get_page_size(request) == 100

    def test_returns_default_on_invalid_value(self) -> None:
        request = MagicMock()
        request.query_params = {"page_size": "abc"}
        assert self.pagination.get_page_size(request) == 10

    def test_returns_default_on_none_value(self) -> None:
        request = MagicMock()
        request.query_params = {"page_size": None}
        assert self.pagination.get_page_size(request) == 10
