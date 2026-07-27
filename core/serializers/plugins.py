"""Default serializer plugins for the enterprise platform."""

from typing import TYPE_CHECKING

from rest_framework.fields import Field

from core.base.plugins import SerializerPlugin

if TYPE_CHECKING:
    from core.base.serializers import BaseSerializer


class NonEditableFieldsSerializerPlugin(SerializerPlugin):
    """Marks fields read-only based on their underlying model field properties.

    A field is marked read-only if its model field satisfies any of:
    - primary_key=True
    - editable=False
    - auto_now=True
    - auto_now_add=True

    Use Meta.extensions_exclude to opt out on a per-serializer basis.
    """

    def filter_fields(
        self, serializer: BaseSerializer, fields: dict[str, Field]
    ) -> dict[str, Field]:
        """Inspect each field's model field and set read_only where applicable.

        Args:
            serializer: The serializer instance being built.
            fields: The fully resolved field dict from get_fields().

        Returns:
            The same fields dict with read_only set on non-editable fields.
        """
        model = getattr(getattr(serializer, "Meta", None), "model", None)
        if model is None:
            return fields

        model_field_names = {f.name for f in model._meta.get_fields()}

        for field_name, field in fields.items():
            if field_name not in model_field_names:
                continue
            try:
                model_field = model._meta.get_field(field_name)
            except Exception:
                continue
            if (
                getattr(model_field, "primary_key", False)
                or not getattr(model_field, "editable", True)
                or getattr(model_field, "auto_now", False)
                or getattr(model_field, "auto_now_add", False)
            ):
                field.read_only = True

        return fields
