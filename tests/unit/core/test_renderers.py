import json
from unittest.mock import MagicMock

from core.renderers import APIRenderer


class TestAPIRenderer:
    def setup_method(self) -> None:
        self.renderer = APIRenderer()

    def test_success_response_wrapped(self) -> None:
        response = MagicMock()
        response.status_code = 200
        context = {"response": response}

        result = self.renderer.render({"key": "value"}, renderer_context=context)
        parsed = json.loads(result)
        assert parsed["status"] == "OK"
        assert parsed["data"] == {"key": "value"}

    def test_error_response_passthrough(self) -> None:
        response = MagicMock()
        response.status_code = 400
        context = {"response": response}

        error_data = {"status": "ERROR", "code": "validation_error", "data": {}}
        result = self.renderer.render(error_data, renderer_context=context)
        parsed = json.loads(result)
        assert parsed["status"] == "ERROR"
        assert parsed["code"] == "validation_error"

    def test_no_context(self) -> None:
        result = self.renderer.render({"key": "value"}, renderer_context=None)
        parsed = json.loads(result)
        assert parsed["status"] == "OK"
