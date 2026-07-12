"""Tests for global plugin registry and merge logic in BaseSerializer._get_plugins()."""

from typing import Any
from unittest.mock import patch

from core.base.serializers import BaseSerializer, SerializerPlugin


class PluginA(SerializerPlugin):
    def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        pass


class PluginB(SerializerPlugin):
    def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        pass


class PluginC(SerializerPlugin):
    def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        pass


def _make_serializer(
    extensions: list[type[SerializerPlugin]] | None = None,
    extensions_exclude: list[type[SerializerPlugin]] | None = None,
) -> Any:
    """Create a minimal BaseSerializer subclass with given Meta config."""

    meta_attrs: dict[str, Any] = {
        "model": None,
        "fields": "__all__",
        "extensions": extensions or [],
        "extensions_exclude": extensions_exclude or [],
    }
    meta = type("Meta", (), meta_attrs)

    cls = type("TestSerializer", (BaseSerializer,), {"Meta": meta})
    serializer = cls.__new__(cls)  # type: ignore[call-overload]
    serializer.Meta = meta  # type: ignore[attr-defined]
    return serializer


class TestGetPluginsMergeLogic:
    """Tests for global + local - excluded plugin resolution."""

    @patch(
        "core.base.serializers.settings",
    )
    def test_global_plugins_loaded_from_settings(self, mock_settings: Any) -> None:
        mock_settings.SERIALIZER_PLUGINS = [
            "core.tests.test_plugin_registry.PluginA",
        ]
        serializer = _make_serializer()

        plugins = serializer._get_plugins()

        assert len(plugins) == 1
        assert isinstance(plugins[0], PluginA)

    @patch("core.base.serializers.settings")
    def test_local_extensions_merged_with_global(self, mock_settings: Any) -> None:
        mock_settings.SERIALIZER_PLUGINS = [
            "core.tests.test_plugin_registry.PluginA",
        ]
        serializer = _make_serializer(extensions=[PluginB])

        plugins = serializer._get_plugins()

        assert len(plugins) == 2
        assert isinstance(plugins[0], PluginA)
        assert isinstance(plugins[1], PluginB)

    @patch("core.base.serializers.settings")
    def test_excluded_plugins_removed(self, mock_settings: Any) -> None:
        mock_settings.SERIALIZER_PLUGINS = [
            "core.tests.test_plugin_registry.PluginA",
            "core.tests.test_plugin_registry.PluginB",
        ]
        serializer = _make_serializer(extensions_exclude=[PluginA])

        plugins = serializer._get_plugins()

        assert len(plugins) == 1
        assert isinstance(plugins[0], PluginB)

    @patch("core.base.serializers.settings")
    def test_local_plugin_can_be_excluded(self, mock_settings: Any) -> None:
        mock_settings.SERIALIZER_PLUGINS = []
        serializer = _make_serializer(
            extensions=[PluginA, PluginB], extensions_exclude=[PluginB]
        )

        plugins = serializer._get_plugins()

        assert len(plugins) == 1
        assert isinstance(plugins[0], PluginA)

    @patch("core.base.serializers.settings")
    def test_empty_when_all_excluded(self, mock_settings: Any) -> None:
        mock_settings.SERIALIZER_PLUGINS = [
            "core.tests.test_plugin_registry.PluginA",
        ]
        serializer = _make_serializer(extensions_exclude=[PluginA])

        plugins = serializer._get_plugins()

        assert plugins == []

    @patch("core.base.serializers.settings")
    def test_no_global_setting_defaults_to_empty(self, mock_settings: Any) -> None:
        mock_settings.SERIALIZER_PLUGINS = []
        serializer = _make_serializer(extensions=[PluginC])

        plugins = serializer._get_plugins()

        assert len(plugins) == 1
        assert isinstance(plugins[0], PluginC)

    @patch("core.base.serializers.settings")
    def test_order_is_global_then_local(self, mock_settings: Any) -> None:
        mock_settings.SERIALIZER_PLUGINS = [
            "core.tests.test_plugin_registry.PluginB",
        ]
        serializer = _make_serializer(extensions=[PluginA])

        plugins = serializer._get_plugins()

        assert isinstance(plugins[0], PluginB)
        assert isinstance(plugins[1], PluginA)
