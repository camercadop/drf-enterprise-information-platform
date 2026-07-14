"""Tests for core.validators.serializers module."""

from unittest.mock import MagicMock

import pytest
from rest_framework.exceptions import ValidationError

from core.validators.serializers import UniqueTogetherContextValidator


class TestUniqueTogetherContextValidator:
    def test_passes_when_no_duplicate(self) -> None:
        qs = MagicMock()
        qs.filter.return_value.exists.return_value = False

        validator = UniqueTogetherContextValidator(
            fields={"name": "name"},
            queryset=qs,
        )
        serializer = MagicMock()
        serializer.context = {"tenant_id": "t1"}

        validator({"name": "unique"}, serializer)
        qs.filter.assert_called_once_with(name="unique", tenant_id="t1")

    def test_raises_when_duplicate_exists(self) -> None:
        qs = MagicMock()
        qs.filter.return_value.exists.return_value = True

        validator = UniqueTogetherContextValidator(
            fields={"name": "name"},
            queryset=qs,
        )
        serializer = MagicMock()
        serializer.context = {"tenant_id": "t1"}

        with pytest.raises(ValidationError, match="already exists"):
            validator({"name": "duplicate"}, serializer)

    def test_custom_message(self) -> None:
        qs = MagicMock()
        qs.filter.return_value.exists.return_value = True

        validator = UniqueTogetherContextValidator(
            fields={"code": "code"},
            queryset=qs,
            message="Code must be unique.",
        )
        serializer = MagicMock()
        serializer.context = {"tenant_id": "t1"}

        with pytest.raises(ValidationError, match="Code must be unique"):
            validator({"code": "dup"}, serializer)

    def test_custom_context_fields(self) -> None:
        qs = MagicMock()
        qs.filter.return_value.exists.return_value = False

        validator = UniqueTogetherContextValidator(
            fields={"name": "name"},
            context_fields={"org_id": "org_id"},
            queryset=qs,
        )
        serializer = MagicMock()
        serializer.context = {"org_id": "org-123"}

        validator({"name": "test"}, serializer)
        qs.filter.assert_called_once_with(name="test", org_id="org-123")

    def test_infers_queryset_from_serializer_meta(self) -> None:
        mock_model = MagicMock()
        mock_qs = MagicMock()
        mock_model.objects.all.return_value = mock_qs
        mock_qs.filter.return_value.exists.return_value = False

        validator = UniqueTogetherContextValidator(fields={"name": "name"})

        serializer = MagicMock()
        serializer.Meta.model = mock_model
        serializer.context = {"tenant_id": "t1"}

        validator({"name": "test"}, serializer)
        mock_model.objects.all.assert_called_once()
        mock_qs.filter.assert_called_once_with(name="test", tenant_id="t1")
