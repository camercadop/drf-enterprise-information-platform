# Fields

Custom DRF serializer fields for the enterprise platform.

## Structure

```
core/fields/
└── related.py   # Foreign key fields
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
| `representation_fields` | `list[str] \| None` | `None` | Fields to include in the nested output. Supports `__` traversal (e.g. `role__name`). Takes precedence over model-level config |

### Nested Representation

`to_representation` returns a dict instead of a plain primary key. Field resolution order for each entry in `representation_fields`:

1. Serializer hook `get_<field>_representation(instance)` on the parent serializer (root level only)
2. Model instance hook `get_<field>_representation()` on the current instance
3. Dotted traversal via `__`: at each level, tries `get_<segment>()` on the current instance before falling back to `getattr`, then recurses with the remaining path applying the same hook cascade. For example, `role__name__suffix` tries:
   - `get_role__name__suffix_representation()` on root instance
   - `get_name__suffix_representation()` on `role` instance (resolved via `get_role()` or `getattr`)
   - `get_suffix_representation()` on `name` instance (resolved via `get_name()` or `getattr`)
   - `getattr(name_instance, "suffix")` as final fallback
4. Direct `getattr(instance, field_name)`
5. Returns `None` with a warning log if nothing resolves

If no `representation_fields` are configured at field level, the field checks `fk_representation_fields` as a class attribute on the related model. If neither is set, the fallback is `{"id": str(instance.pk), "label": str(instance)}`. If a resolved value is itself a model instance, it is represented recursively using the same logic. If a resolved value is a `QuerySet` or `list`, each item is represented recursively.

```python
# Field-level configuration
class MembershipSerializer(serializers.Serializer):
    user = ForeignKeyField(
        queryset=User.objects.all(),
        representation_fields=["id", "email", "role__name"],
    )

# Model-level configuration
class TenantRole(BaseModel):
    fk_representation_fields = ["id", "name"]
    name = models.CharField(max_length=100)

# Serializer hook
class MembershipSerializer(serializers.Serializer):
    user = ForeignKeyField(queryset=User.objects.all(), representation_fields=["id", "display"])

    def get_display_representation(self, instance: User) -> str:
        return f"{instance.first_name} {instance.last_name}"

# Recursive representation — membership.user is a model instance,
# represented automatically using User.fk_representation_fields
class TeamMembershipSerializer(serializers.Serializer):
    membership = ForeignKeyField(read_only=True, representation_fields=["id", "user"])
```
