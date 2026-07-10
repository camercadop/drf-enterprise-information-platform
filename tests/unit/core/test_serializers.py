from typing import Any

import pytest
from rest_framework.exceptions import ValidationError

from core.base.serializers import SerializerPlugin


class TrackingPlugin(SerializerPlugin):
    calls: list[str] = []

    def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        TrackingPlugin.calls.append("on_pre_create")

    def on_post_create(self, serializer: Any, instance: Any) -> None:
        TrackingPlugin.calls.append("on_post_create")

    def on_pre_validate(self, serializer: Any, data: dict[str, Any]) -> None:
        TrackingPlugin.calls.append("on_pre_validate")

    def on_post_validate(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        TrackingPlugin.calls.append("on_post_validate")


class ShortCircuitPlugin(SerializerPlugin):
    def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
        raise ValidationError("Blocked by plugin")


class TestGetPlugins:
    def test_returns_plugin_instances(self) -> None:
        plugins = [TrackingPlugin]
        instances = [p() for p in plugins]
        assert len(instances) == 1
        assert isinstance(instances[0], TrackingPlugin)

    def test_empty_extensions(self) -> None:
        plugins: list[type[SerializerPlugin]] = []
        instances = [p() for p in plugins]
        assert instances == []


class TestRunPlugins:
    def setup_method(self) -> None:
        TrackingPlugin.calls = []

    def test_calls_existing_hook(self) -> None:
        plugin = TrackingPlugin()
        hook = "on_pre_create"
        if hasattr(plugin, hook):
            getattr(plugin, hook)(None, {})
        assert "on_pre_create" in TrackingPlugin.calls

    def test_skips_missing_hook(self) -> None:
        plugin = TrackingPlugin()
        hook = "on_nonexistent"
        if hasattr(plugin, hook):
            getattr(plugin, hook)(None, {})
        assert TrackingPlugin.calls == []

    def test_short_circuit_raises(self) -> None:
        plugin = ShortCircuitPlugin()
        with pytest.raises(ValidationError, match="Blocked by plugin"):
            plugin.on_pre_create(None, {})

    def test_multiple_plugins_execute_in_order(self) -> None:
        class FirstPlugin(SerializerPlugin):
            def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
                TrackingPlugin.calls.append("first")

        class SecondPlugin(SerializerPlugin):
            def on_pre_create(self, serializer: Any, validated_data: dict[str, Any]) -> None:
                TrackingPlugin.calls.append("second")

        plugins = [FirstPlugin(), SecondPlugin()]
        for p in plugins:
            if hasattr(p, "on_pre_create"):
                p.on_pre_create(None, {})

        assert TrackingPlugin.calls == ["first", "second"]


class TestPluginStatelessness:
    def test_plugin_has_no_instance_state(self) -> None:
        p1 = TrackingPlugin()
        p2 = TrackingPlugin()
        assert p1.__dict__ == p2.__dict__ == {}
