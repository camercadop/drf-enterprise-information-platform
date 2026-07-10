# Fields

Custom DRF serializer fields for the enterprise platform.

## Structure

```
core/fields/
└── related.py   # Foreign key fields with configurable filtering
```

## API

### related.py

- `ForeignKeyField` — a `PrimaryKeyRelatedField` with configurable static filters, context-resolved filters, and soft-delete exclusion

```python
from core.fields import ForeignKeyField

class MembershipCreateSerializer(serializers.Serializer):
    # Platform-level lookup (no tenant scoping, no soft-delete)
    user_id = ForeignKeyField(
        queryset=User.objects.all(),
        base_filters={"is_active": True},
        context_filters={},
        exclude_deleted=False,
        error_message="User not found or inactive.",
    )

    # Tenant-scoped lookup (default context_filters and exclude_deleted)
    role_id = ForeignKeyField(
        queryset=TenantRole.objects.all(),
        error_message="Role not found in this tenant.",
    )
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_filters` | `dict[str, object] \| None` | `None` | Static queryset filters applied unconditionally |
| `context_filters` | `dict[str, str] \| None` | `{"tenant_id": "tenant_id"}` | Mapping of queryset lookup keys to serializer context keys, resolved at validation time |
| `exclude_deleted` | `bool` | `True` | Whether to append `.filter(deleted_at__isnull=True)` |
| `error_message` | `str` | `"Object not found."` | Custom error message for "does not exist" failures |
