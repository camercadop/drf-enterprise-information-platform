from typing import Any
from unittest.mock import MagicMock

from rest_framework import serializers

from core.serializers.plugins import NonEditableFieldsSerializerPlugin


def _make_serializer(model: Any) -> Any:
    """Build a minimal serializer mock with a Meta.model attribute."""
    serializer = MagicMock()
    serializer.Meta.model = model
    return serializer


def _make_model(*fields: Any) -> Any:
    """Build a minimal model mock with _meta.get_fields() and _meta.get_field()."""
    model = MagicMock()
    model._meta.get_fields.return_value = fields
    model._meta.get_field.side_effect = lambda name: next(
        f for f in fields if f.name == name
    )
    return model


def _make_model_field(name: str, **attrs: Any) -> Any:
    """Build a model field mock with the given attributes."""
    field = MagicMock()
    field.name = name
    field.configure_mock(**attrs)
    return field


class TestNonEditableFieldsSerializerPlugin:
    def setup_method(self) -> None:
        self.plugin = NonEditableFieldsSerializerPlugin()

    def _run(self, model: Any, serializer_fields: dict[str, Any]) -> dict[str, Any]:
        serializer = _make_serializer(model)
        return self.plugin.filter_fields(serializer, serializer_fields)

    def test_primary_key_field_is_marked_read_only(self) -> None:
        model_field = _make_model_field("id", primary_key=True, editable=False, auto_now=False, auto_now_add=False)
        model = _make_model(model_field)
        field = serializers.UUIDField()
        result = self._run(model, {"id": field})
        assert result["id"].read_only is True

    def test_non_editable_field_is_marked_read_only(self) -> None:
        model_field = _make_model_field("code", primary_key=False, editable=False, auto_now=False, auto_now_add=False)
        model = _make_model(model_field)
        field = serializers.CharField()
        result = self._run(model, {"code": field})
        assert result["code"].read_only is True

    def test_auto_now_field_is_marked_read_only(self) -> None:
        model_field = _make_model_field("updated_at", primary_key=False, editable=False, auto_now=True, auto_now_add=False)
        model = _make_model(model_field)
        field = serializers.DateTimeField()
        result = self._run(model, {"updated_at": field})
        assert result["updated_at"].read_only is True

    def test_auto_now_add_field_is_marked_read_only(self) -> None:
        model_field = _make_model_field("created_at", primary_key=False, editable=False, auto_now=False, auto_now_add=True)
        model = _make_model(model_field)
        field = serializers.DateTimeField()
        result = self._run(model, {"created_at": field})
        assert result["created_at"].read_only is True

    def test_normal_editable_field_is_not_modified(self) -> None:
        model_field = _make_model_field("title", primary_key=False, editable=True, auto_now=False, auto_now_add=False)
        model = _make_model(model_field)
        field = serializers.CharField()
        result = self._run(model, {"title": field})
        assert result["title"].read_only is False

    def test_field_not_on_model_is_not_modified(self) -> None:
        model = _make_model()
        field = serializers.CharField()
        field.read_only = False
        result = self._run(model, {"virtual": field})
        assert result["virtual"].read_only is False

    def test_no_meta_model_returns_fields_unchanged(self) -> None:
        serializer = MagicMock()
        serializer.Meta.model = None
        field = serializers.CharField()
        field.read_only = False
        result = self.plugin.filter_fields(serializer, {"title": field})
        assert result["title"].read_only is False
