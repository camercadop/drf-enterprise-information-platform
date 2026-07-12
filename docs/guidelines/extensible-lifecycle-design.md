# Extensible Lifecycle Design

This document describes the pattern used to extend behavior in lifecycle-driven classes (serializers, views, services).

---

## Overview

The pattern combines two complementary mechanisms:

- **Plugins** — stateless, reusable classes that participate in lifecycle events across multiple classes. They handle cross-cutting concerns (audit, soft-delete, feature flags, etc.).
- **Template methods** — internal hook points (`pre_*/do_*/post_*`) that subclasses override to customize specific steps without rewriting the full flow.

Plugins are the **outer layer** (horizontal). Template methods are the **inner layer** (vertical).

---

## Execution Order

```
Plugin.on_pre_create(serializer, validated_data)
  Serializer.pre_create(validated_data)
  Serializer.do_create(validated_data)        → performs the actual operation
  Serializer.post_create(instance, validated_data)
Plugin.on_post_create(serializer, instance)
```

---

## Plugins

### Defining a Plugin

Subclass `SerializerPlugin` and override only the hooks you need:

```python
from core.base.serializers import BaseSerializer, SerializerPlugin

class AuditPlugin(SerializerPlugin):
    def on_pre_create(self, serializer: BaseSerializer, validated_data: dict) -> None:
        request = serializer.context.get("request")
        if request and request.user:
            validated_data["created_by"] = str(request.user)

    def on_pre_update(self, serializer: BaseSerializer, instance, validated_data: dict) -> None:
        request = serializer.context.get("request")
        if request and request.user:
            validated_data["updated_by"] = str(request.user)
```

### Registering Plugins

#### Global Plugins (settings-based)

Plugins declared in `settings.SERIALIZER_PLUGINS` apply to every serializer that inherits from `BaseSerializer`. Each plugin decides internally whether to act (e.g., by inspecting the model for a specific field).

```python
# config/settings/base.py
SERIALIZER_PLUGINS: list[str] = [
    "apps.tenants.plugins.TenantInjectionSerializerPlugin",
]
```

#### Local Plugins (per-serializer)

Declare plugins in `Meta.extensions` to add them for a specific serializer:

```python
class CompanySerializer(BaseSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "created_by"]
        extensions = [AuditPlugin, SoftDeletablePlugin]
```

#### Excluding Plugins

Use `Meta.extensions_exclude` to opt out of global or local plugins:

```python
class PlatformReportSerializer(BaseSerializer):
    class Meta:
        model = PlatformReport
        fields = ["id", "title"]
        extensions_exclude = [TenantInjectionSerializerPlugin]
```

#### Resolution Order

```
final plugins = global (settings.SERIALIZER_PLUGINS, in order)
               + local (Meta.extensions, in order)
               - excluded (Meta.extensions_exclude)
```

Global plugins execute first, then local plugins.

### Rules

- Plugins are **stateless**. They receive the serializer as argument for context access.
- Plugins can **mutate** `validated_data` in `on_pre_create`/`on_pre_update`.
- Plugins can **short-circuit** by raising any exception (typically DRF exceptions).
- Plugins execute in **resolution order** (global first, then local, left to right within each group).
- There are **no dependencies** between plugins.
- Global plugins must be **self-guarding** — they check applicability (e.g., model has `tenant_id`) and no-op otherwise.

### Available Hooks

| Hook | Receives | Purpose |
|------|----------|---------|
| `on_pre_create` | serializer, validated_data | Before creation flow |
| `on_post_create` | serializer, instance | After creation flow |
| `on_pre_update` | serializer, instance, validated_data | Before update flow |
| `on_post_update` | serializer, instance | After update flow |
| `on_pre_validate` | serializer, data | Before validation flow |
| `on_post_validate` | serializer, validated_data | After validation flow |
| `on_representation` | serializer, instance, representation | Transforms output (must return dict) |

---

## Template Methods

### Purpose

Allow subclasses to customize a specific step of the lifecycle without overriding the entire `create`/`update`/`validate` method.

### Available Hooks

**Create:**
- `pre_create(validated_data)` — prepare data before saving
- `do_create(validated_data)` — perform the actual save (override for custom creation logic)
- `post_create(instance, validated_data)` — side effects after creation

**Update:**
- `pre_update(instance, validated_data)` — prepare data before saving
- `do_update(instance, validated_data)` — perform the actual save
- `post_update(instance, validated_data)` — side effects after update

**Validate:**
- `pre_validate(attrs)` — checks before validation
- `do_validate(attrs)` — core validation logic (must return attrs)
- `post_validate(attrs)` — checks after validation

### Example

```python
class InvitationSerializer(BaseSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "email", "token"]
        extensions = [AuditPlugin]

    def pre_create(self, validated_data: dict) -> None:
        validated_data["token"] = generate_token()

    def post_create(self, instance, validated_data: dict) -> None:
        send_invitation_email(instance)
```

---

## View-Level Declarative Permissions

`BaseViewSet` supports a `write_permission_classes` attribute that eliminates the need to override `get_permissions` for the common pattern of "elevated permissions on write actions, authenticated-only on reads."

```python
class TenantViewSet(BaseViewSet):
    write_permission_classes = [IsSuperUser]
```

When `write_permission_classes` is set, write actions (`create`, `update`, `partial_update`, `destroy`) require `IsAuthenticated` plus the listed permissions. Read actions fall back to `permission_classes` (default: `IsAuthenticated`).

For non-standard permission logic (e.g., per-action granularity beyond read/write), override `get_permissions` as usual.

---

## When to Use Each

| Scenario | Use |
|----------|-----|
| Behavior shared across many serializers (audit, soft-delete, tenant injection) | Plugin |
| Behavior specific to one serializer (generate token, send email) | Template method |
| Blocking an operation based on a condition | Plugin (raise exception) |
| Customizing how an object is saved | Template method (`do_create`) |
| Transforming API response shape | Plugin (`on_representation`) |
| Elevated permissions on write actions | `write_permission_classes` attribute |
