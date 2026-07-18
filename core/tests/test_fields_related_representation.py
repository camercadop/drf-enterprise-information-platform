"""Tests for ForeignKeyField nested representation methods."""

import uuid
from unittest.mock import MagicMock

import pytest

from core.fields.related import ForeignKeyField


def _make_field(**kwargs: object) -> ForeignKeyField:
    field = ForeignKeyField(queryset=MagicMock(), context_filters={}, **kwargs)
    field.bind("user", None)
    return field


def _make_instance(**attrs: object) -> MagicMock:
    instance = MagicMock(spec=object)
    instance.pk = uuid.UUID("00000000-0000-0000-0000-000000000001")
    instance.__str__ = lambda self: "Instance"
    for key, value in attrs.items():
        setattr(instance, key, value)
    return instance


class TestResolveFieldValue:
    def test_direct_attribute(self) -> None:
        field = _make_field()
        instance = _make_instance(name="Alice")
        assert field._resolve_field_value("name", instance) == "Alice"

    def test_missing_field_returns_none_and_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        field = _make_field()
        instance = MagicMock(spec=object)
        with caplog.at_level("WARNING"):
            result = field._resolve_field_value("missing", instance)
        assert result is None
        assert "missing" in caplog.text

    def test_model_hook_takes_priority_over_getattr(self) -> None:
        field = _make_field()
        instance = _make_instance(name="raw")
        instance.get_name_representation = lambda: "hooked"
        assert field._resolve_field_value("name", instance) == "hooked"

    def test_serializer_hook_takes_priority_over_model_hook(self) -> None:
        field = _make_field()
        instance = _make_instance()
        instance.get_name_representation = lambda: "model-hook"
        serializer = MagicMock()
        serializer.get_name_representation = lambda inst: "serializer-hook"
        assert field._resolve_field_value("name", instance, serializer) == "serializer-hook"

    def test_serializer_hook_not_consulted_on_recursive_call(self) -> None:
        field = _make_field()
        role = _make_instance(name="Engineer")
        instance = _make_instance(role=role)
        serializer = MagicMock(spec=[])
        result = field._resolve_field_value("role__name", instance, serializer)
        assert result == "Engineer"

    def test_dotted_traversal_two_levels(self) -> None:
        field = _make_field()
        role = _make_instance(name="Engineer")
        instance = _make_instance(role=role)
        assert field._resolve_field_value("role__name", instance) == "Engineer"

    def test_dotted_traversal_three_levels(self) -> None:
        field = _make_field()
        suffix = MagicMock(spec=object)
        suffix.value = "Sr"
        name = _make_instance(suffix=suffix)
        role = _make_instance(name=name)
        instance = _make_instance(role=role)
        assert field._resolve_field_value("role__name__suffix", instance) == name.suffix

    def test_dotted_traversal_model_hook_at_intermediate_level(self) -> None:
        field = _make_field()
        role = _make_instance()
        role.get_name_representation = lambda: "hooked-name"
        instance = _make_instance(role=role)
        assert field._resolve_field_value("role__name", instance) == "hooked-name"

    def test_dotted_traversal_uses_get_hook_for_related_object(self) -> None:
        field = _make_field()
        role = _make_instance(name="Engineer")
        instance = _make_instance()
        instance.get_role = lambda: role
        assert field._resolve_field_value("role__name", instance) == "Engineer"

    def test_dotted_traversal_returns_none_on_missing_segment(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        field = _make_field()
        instance = _make_instance(role=None)
        with caplog.at_level("WARNING"):
            result = field._resolve_field_value("role__name", instance)
        assert result is None
        assert "role" in caplog.text


class TestToRepresentation:
    def test_fallback_when_no_config(self) -> None:
        field = _make_field()
        instance = MagicMock(spec=object)
        instance.pk = uuid.UUID("00000000-0000-0000-0000-000000000001")
        instance.__str__ = lambda self: "Alice"
        assert field.to_representation(instance) == {
            "id": "00000000-0000-0000-0000-000000000001",
            "label": "Alice",
        }

    def test_uses_field_level_representation_fields(self) -> None:
        field = _make_field(representation_fields=["id", "name"])
        instance = _make_instance(id="abc", name="Alice")
        assert field.to_representation(instance) == {"id": "abc", "name": "Alice"}

    def test_uses_model_fk_representation_fields(self) -> None:
        field = _make_field()

        class FakeModel:
            fk_representation_fields = ["id", "email"]
            id = "abc"
            email = "alice@example.com"

        assert field.to_representation(FakeModel()) == {"id": "abc", "email": "alice@example.com"}

    def test_field_level_wins_over_model_attribute(self) -> None:
        field = _make_field(representation_fields=["id"])

        class FakeModel:
            fk_representation_fields = ["id", "email"]
            id = "abc"
            email = "alice@example.com"

        assert field.to_representation(FakeModel()) == {"id": "abc"}

    def test_passes_parent_serializer_to_resolve(self) -> None:
        field = _make_field(representation_fields=["display"])
        serializer = MagicMock()
        serializer.get_display_representation = lambda inst: "custom"
        field.parent = serializer
        instance = _make_instance()
        assert field.to_representation(instance) == {"display": "custom"}


class TestRepresentInstance:
    def test_nested_model_instance_is_represented_recursively(self) -> None:
        from django.db.models import Model

        field = _make_field(representation_fields=["id", "role"])

        class FakeRole(Model):
            class Meta:
                app_label = "tests"

        role = FakeRole.__new__(FakeRole)
        object.__setattr__(role, "pk", uuid.UUID("00000000-0000-0000-0000-000000000002"))

        instance = _make_instance(id="abc", role=role)
        result = field.to_representation(instance)
        assert result == {
            "id": "abc",
            "role": {"id": "00000000-0000-0000-0000-000000000002", "label": str(role)},
        }

    def test_nested_model_instance_uses_its_own_fk_representation_fields(self) -> None:
        from django.db.models import Model

        field = _make_field(representation_fields=["id", "role"])

        class FakeRole(Model):
            fk_representation_fields = ["id", "name"]

            class Meta:
                app_label = "tests"

        role = FakeRole.__new__(FakeRole)
        object.__setattr__(role, "pk", uuid.UUID("00000000-0000-0000-0000-000000000002"))
        role.id = uuid.UUID("00000000-0000-0000-0000-000000000002")  # type: ignore[attr-defined]
        role.name = "Admin"  # type: ignore[attr-defined]

        instance = _make_instance(id="abc", role=role)
        result = field.to_representation(instance)
        assert result == {
            "id": "abc",
            "role": {"id": uuid.UUID("00000000-0000-0000-0000-000000000002"), "name": "Admin"},
        }
