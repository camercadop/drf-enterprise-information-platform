# Serializers

Default serializer plugins for the enterprise platform.

## Structure

```
core/serializers/
└── plugins.py   # Default serializer plugins
```

## API

### plugins.py

- `NonEditableFieldsSerializerPlugin` — marks fields read-only based on their underlying model field properties

A field is marked read-only if its model field satisfies any of:

| Property | Example fields |
|----------|---------------|
| `primary_key=True` | `id` |
| `editable=False` | any field with `editable=False` |
| `auto_now=True` | `updated_at` |
| `auto_now_add=True` | `created_at` |

Registered globally via `DEFAULT_SERIALIZER_PLUGINS`. Opt out per serializer via `Meta.extensions_exclude`:

```python
from core.serializers.plugins import NonEditableFieldsSerializerPlugin

class MySerializer(DefaultModelSerializer):
    class Meta(DefaultModelSerializer.Meta):
        model = MyModel
        fields = ["id", "name"]
        extensions_exclude = [NonEditableFieldsSerializerPlugin]
```
