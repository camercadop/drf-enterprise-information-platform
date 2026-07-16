"""Tests for BaseSerializer lifecycle (create, update, validate)."""

from typing import Any
from unittest.mock import MagicMock, patch

from django.db import models

from core.base.serializers import BaseSerializer, SerializerPlugin


class FakeModel(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)

    class Meta:
        app_label = "fake"


class FakeSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = FakeModel
        fields = ["id", "name", "slug", "created_at", "updated_at"]


class RecordingPlugin(SerializerPlugin):
    """Plugin that records hook calls for assertion."""

    calls: list[str] = []

    def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        RecordingPlugin.calls.append("on_pre_create")

    def on_post_create(self, serializer: Any, instance: Any) -> None:
        RecordingPlugin.calls.append("on_post_create")

    def on_pre_update(self, serializer: Any, instance: Any, validated_data: dict[str, Any]) -> None:
        RecordingPlugin.calls.append("on_pre_update")

    def on_post_update(self, serializer: Any, instance: Any) -> None:
        RecordingPlugin.calls.append("on_post_update")

    def on_pre_validate(self, serializer: Any, data: dict[str, Any]) -> None:
        RecordingPlugin.calls.append("on_pre_validate")

    def on_post_validate(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        RecordingPlugin.calls.append("on_post_validate")


class TestBaseSerializerCreate:
    def setup_method(self) -> None:
        RecordingPlugin.calls = []

    @patch.object(FakeSerializer, "_get_plugins", return_value=[RecordingPlugin()])
    def test_create_calls_plugins_and_hooks(self, mock_plugins: Any) -> None:
        serializer = FakeSerializer()
        instance = MagicMock()

        with patch.object(serializer, "do_create", return_value=instance) as mock_do:
            result = serializer.create({"name": "test"})

        mock_do.assert_called_once_with({"name": "test"})
        assert result == instance
        assert "on_pre_create" in RecordingPlugin.calls
        assert "on_post_create" in RecordingPlugin.calls

    @patch.object(FakeSerializer, "_get_plugins", return_value=[])
    def test_do_create_saves_model(self, mock_plugins: Any) -> None:
        serializer = FakeSerializer()
        mock_instance = MagicMock()

        with patch.object(FakeModel, "__init__", return_value=None) as mock_init:
            with patch.object(FakeModel, "save") as mock_save:
                mock_init.return_value = None
                result = serializer.do_create({"name": "test"})

        mock_save.assert_called_once()

    @patch.object(FakeSerializer, "_get_plugins", return_value=[])
    def test_pre_create_hook_called(self, mock_plugins: Any) -> None:
        serializer = FakeSerializer()
        called = []

        def custom_pre_create(validated_data: dict[str, Any]) -> None:
            called.append("pre_create")

        serializer.pre_create = custom_pre_create  # type: ignore[assignment]

        with patch.object(serializer, "do_create", return_value=MagicMock()):
            serializer.create({"name": "test"})

        assert "pre_create" in called


class TestBaseSerializerUpdate:
    def setup_method(self) -> None:
        RecordingPlugin.calls = []

    @patch.object(FakeSerializer, "_get_plugins", return_value=[RecordingPlugin()])
    def test_update_calls_plugins_and_hooks(self, mock_plugins: Any) -> None:
        serializer = FakeSerializer()
        instance = MagicMock()

        with patch.object(serializer, "do_update", return_value=instance):
            result = serializer.update(instance, {"name": "updated"})

        assert result == instance
        assert "on_pre_update" in RecordingPlugin.calls
        assert "on_post_update" in RecordingPlugin.calls

    @patch.object(FakeSerializer, "_get_plugins", return_value=[])
    def test_do_update_sets_attrs_and_saves(self, mock_plugins: Any) -> None:
        serializer = FakeSerializer()
        instance = MagicMock()

        result = serializer.do_update(instance, {"name": "new_name"})

        assert instance.name == "new_name"
        instance.save.assert_called_once()
        assert result == instance


class TestBaseSerializerValidate:
    def setup_method(self) -> None:
        RecordingPlugin.calls = []

    @patch.object(FakeSerializer, "_get_plugins", return_value=[RecordingPlugin()])
    def test_validate_calls_plugins(self, mock_plugins: Any) -> None:
        serializer = FakeSerializer()
        result = serializer.validate({"name": "test"})

        assert result == {"name": "test"}
        assert "on_pre_validate" in RecordingPlugin.calls
        assert "on_post_validate" in RecordingPlugin.calls

    @patch.object(FakeSerializer, "_get_plugins", return_value=[])
    def test_do_validate_returns_attrs(self, mock_plugins: Any) -> None:
        serializer = FakeSerializer()
        attrs = {"name": "test", "slug": "test-slug"}
        result = serializer.do_validate(attrs)
        assert result == attrs


class TestBaseSerializerValidateSlug:
    def test_validate_slug_returns_value_when_provided(self) -> None:
        serializer = FakeSerializer()
        assert serializer.validate_slug("my-slug") == "my-slug"

    def test_validate_slug_generates_from_name_when_empty(self) -> None:
        serializer = FakeSerializer(data={"name": "My Resource", "slug": ""})
        serializer.initial_data = {"name": "My Resource"}
        result = serializer.validate_slug("")
        assert result == "my-resource"


class TestBaseSerializerGetPlugins:
    @patch("core.base.serializers.settings")
    def test_loads_global_plugins_from_settings(self, mock_settings: Any) -> None:
        mock_settings.REST_FRAMEWORK = {
            "DEFAULT_SERIALIZER_PLUGINS": [
                "core.tests.test_serializers_lifecycle.RecordingPlugin"
            ]
        }
        with patch("core.base.serializers.import_string", return_value=RecordingPlugin):
            serializer = FakeSerializer()
            plugins = serializer._get_plugins()
        assert len(plugins) == 1
        assert isinstance(plugins[0], RecordingPlugin)

    def test_excludes_plugins_in_extensions_exclude(self) -> None:
        class ExcludingSerializer(BaseSerializer):
            class Meta(BaseSerializer.Meta):
                model = FakeModel
                fields = ["id", "name", "created_at", "updated_at"]
                extensions = [RecordingPlugin]
                extensions_exclude = [RecordingPlugin]

        with patch(
            "core.base.serializers.settings",
            REST_FRAMEWORK={"DEFAULT_SERIALIZER_PLUGINS": []},
        ):
            serializer = ExcludingSerializer()
            plugins = serializer._get_plugins()
        assert len(plugins) == 0
