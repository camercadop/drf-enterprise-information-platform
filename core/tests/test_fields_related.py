from unittest.mock import MagicMock

from core.fields.related import ForeignKeyField


class TestForeignKeyFieldInit:
    def test_default_context_filters(self) -> None:
        field = ForeignKeyField(queryset=MagicMock())
        assert field.context_filters == {"tenant_id": "tenant_id"}

    def test_custom_context_filters(self) -> None:
        field = ForeignKeyField(queryset=MagicMock(), context_filters={"org_id": "org_id"})
        assert field.context_filters == {"org_id": "org_id"}

    def test_empty_context_filters(self) -> None:
        field = ForeignKeyField(queryset=MagicMock(), context_filters={})
        assert field.context_filters == {}

    def test_default_exclude_deleted(self) -> None:
        field = ForeignKeyField(queryset=MagicMock())
        assert field.exclude_deleted is True

    def test_exclude_deleted_false(self) -> None:
        field = ForeignKeyField(queryset=MagicMock(), exclude_deleted=False)
        assert field.exclude_deleted is False

    def test_default_base_filters(self) -> None:
        field = ForeignKeyField(queryset=MagicMock())
        assert field.base_filters == {}

    def test_custom_base_filters(self) -> None:
        field = ForeignKeyField(queryset=MagicMock(), base_filters={"is_active": True})
        assert field.base_filters == {"is_active": True}

    def test_custom_error_message(self) -> None:
        field = ForeignKeyField(queryset=MagicMock(), error_message="Not found!")
        assert field.custom_error_message == "Not found!"

    def test_default_error_message(self) -> None:
        field = ForeignKeyField(queryset=MagicMock())
        assert field.custom_error_message == "Object not found."
