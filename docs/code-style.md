# Code Style

How the code should look — formatting, structure, naming, and structural conventions. This file is the single source of truth for style decisions.

---

## Type Safety

- All function parameters must have type annotations
- Use `X | None` instead of `Optional[X]`
- Avoid returning untyped values from typed functions
- Do not use `from __future__ import annotations` — Python 3.14 supports all modern annotation syntax natively

## Naming

- Files: lowercase with underscores (`base_serializer.py`)
- Classes: PascalCase (`BaseSerializer`)
- Serializer plugins: PascalCase ending in `SerializerPlugin` (`AuditSerializerPlugin`)
- ViewSet plugins: PascalCase ending in `ViewSetPlugin` (`TenantContextViewSetPlugin`)
- Template hooks: `pre_*`, `do_*`, `post_*`
- Plugin hooks: `on_pre_*`, `on_post_*`, `on_*`

## Models

- All tenant-scoped models inherit from `TenantAwareModel` (includes timestamps + soft-delete + tenant FK + `TenantManager` for ORM-level tenant isolation)
- Use `BaseModel` for platform-level models that don't belong to a tenant
- All models use UUID as primary key (`primary_key=True`)
- Do not set `default_auto_field` in app configs
- Add a comment under each field explaining its purpose
- Soft-delete fields: `deleted_at`, `deleted_by`
- Timestamp fields: `created_at`, `updated_at`
- Separate each field + comment pair with one blank line

## Serializers

- Inherit from `DefaultModelSerializer` for standard model serializers — it composes `StandardFieldsSerializerMixin`, `SoftDeletableSerializerMixin`, and `BaseSerializer`
- Inherit directly from `BaseSerializer` only when the standard field set or soft-delete representation is not appropriate
- Annotate `validated_data` as `dict[str, Any]`
- Do not add fields to `read_only_fields` that are already covered by `NonEditableFieldsSerializerPlugin` — it automatically marks fields read-only when the model field has `primary_key=True`, `editable=False`, `auto_now=True`, or `auto_now_add=True`. Only use `read_only_fields` for fields that don't fall into any of those categories

### Plugins

- Use plugins for cross-cutting concerns
- Declare per-serializer plugins via `Meta.extensions: list[type[SerializerPlugin]]` — they are appended to the global plugin set
- Opt out of specific global or local plugins via `Meta.extensions_exclude: list[type[SerializerPlugin]]`
- Global plugins run first (in settings order), then local plugins (in declaration order)

### Template hooks

- Use template methods for per-serializer customization — never override `create`, `update`, or `validate` directly
- Create lifecycle: `pre_create(validated_data)` → `do_create(validated_data)` → `post_create(instance, validated_data)`
- Update lifecycle: `pre_update(instance, validated_data)` → `do_update(instance, validated_data)` → `post_update(instance, validated_data)`
- Validate lifecycle: `pre_validate(attrs)` → `do_validate(attrs)` → `post_validate(attrs)`

## Views

- Inherit from `BaseViewSet` for full CRUD resources
- Inherit from `BaseReadOnlyViewSet` for list + retrieve only (e.g., audit logs, system events)
- Inherit from `BaseGenericViewSet` when composing a custom subset of mixins
- Use `APIView` for single-action endpoints (login, logout, password change)
- Use `serializer_classes: dict[str, type[Serializer]]` for per-action serializer mapping instead of overriding `get_serializer_class`
- Use `querysets: dict[str, QuerySet]` for per-action queryset mapping instead of overriding `get_queryset` when the only difference is the queryset
- Use `write_permission_classes` for elevated write permissions instead of overriding `get_permissions`
- Use `tenant_scoping = False` on viewsets that must not be tenant-filtered (e.g., `TenantViewSet` itself)
- Default behavior is active unless explicitly disabled per-viewset via a class attribute — the safe path is always the default
- Per-viewset customization is declared via class attributes, not by overriding methods
- Use `parent_lookup_fields: dict[str, str]` on nested resource viewsets — maps URL kwargs to model field names; the base viewset auto-filters the queryset and injects parent FK values into `clean_create_data`
- Lifecycle hooks: `pre_create(serializer)`/`post_create(instance)`, `pre_update(serializer)`/`post_update(instance)`, `pre_destroy(instance)`/`post_destroy(instance)`
- Data preparation: `clean_create_data`/`clean_update_data` for raw request data manipulation before serializer instantiation

## URLs & Routing

- All API endpoints live under `/api/`
- Use `DefaultRouter` for viewsets, manual `path()` for `APIView` endpoints
- Each app defines its own `urls.py` with `app_name` set
- URL pattern: `/api/{domain}/{resource}/` (plural nouns, no verbs)
- Detail endpoints: `/api/{domain}/{resource}/{uuid}/`
- Custom actions: `/api/{domain}/{resource}/{uuid}/{action}/` or `/api/{domain}/{action}/`

## Error Handling

- Use the custom exception hierarchy from `core.exceptions` — never raise raw DRF exceptions
- Exception classes and when to use them:
  - `ValidationError` (400) — invalid input, business rule violations
  - `AuthenticationError` (401) — failed credentials, expired tokens
  - `PermissionDeniedError` (403) — authenticated but not authorized
  - `NotFoundError` (404) — resource does not exist or is soft-deleted
  - `ThrottlingError` (429) — rate limit exceeded
- Let the custom exception handler (`core.exceptions.handler`) wrap errors into the standard envelope
- For serializer-level validation, raise DRF's `serializers.ValidationError` (the handler normalizes it)

## Filters

- Use `SmartFilterBackend` from `core.filters.base` instead of `DjangoFilterBackend` — it auto-generates filters for all supported lookups (`exact`, `gte`, `lte`, `gt`, `lt`, `icontains`, `in`, `isnull`) from `filterset_fields` without explicit declarations
- Use `SoftDeleteFilterBackend` from `core.filters.base` to exclude soft-deleted objects by default; superusers and tenant admins may pass `?include_deleted=true` to include them
- Declare `filterset_fields` as a list of field names on the viewset; use `filterset_class` only when the auto-generated filters are insufficient

## Docstrings

- All public classes and methods must have docstrings
- Use Google-style format
- Docstrings must explain the contract (what and why), not restate the implementation (how)
- Include what the method expects, what it guarantees, and when to use alternatives (e.g., hooks instead of overriding)

## Logging

- Every module that emits log output must declare a module-level logger: `logger = logging.getLogger(__name__)`
- Place the logger declaration immediately after all imports, before any class or function definitions
- Use `%s`-style formatting — never f-strings in log calls
- Severity levels:
  - `logger.info` — normal expected events (successful login, resource created)
  - `logger.warning` — security-relevant or unexpected events (failed login, IP blocked, permission denied)
  - `logger.error` — unhandled exceptions; always pass `exc_info=True`
  - `logger.debug` — development-only diagnostics; never in production paths
- Always log security enforcement decisions: failed login, account locked, IP blocked, permission denied
- Never log passwords, tokens, secrets, or full request bodies

## Management Commands

- All commands inherit from `core.base.commands.BaseCommand`, not Django's `BaseCommand` directly
- Command file naming: `verb_noun` format (e.g., `check_permission_catalog.py`, `seed_default_roles.py`)
- Use Rich helpers for all terminal output: `self.success()`, `self.error()`, `self.warning()`, `self.summary_success()`, `self.summary_failure()`
- Never use `print()` in commands
- Always end with a summary line via `summary_success` or `summary_failure`
- `summary_failure` exits with code 1 — required for CI to detect failures

## Settings

- All new app-level settings blocks use the `APP_` prefix (e.g., `APP_SYS_EVENTBUS`, `APP_DMS_INGESTION`)
- Existing settings blocks (`AUTH_LOCKOUT`, `AUTH_RATE_LIMIT`, `AUTH_SESSION`) are not renamed
- All configuration for a feature lives in a single top-level settings dict — no scattered individual keys

## Validators

- Use `UniqueTogetherContextValidator` from `core.validators.serializers` for tenant-scoped uniqueness checks — it combines serializer field values with context values (e.g., `tenant_id`) to enforce uniqueness without relying on database constraints alone
- Declare it in `Meta.validators` on the serializer, not inside `validate()`

## Import Ordering

Managed by Ruff (`isort` rules, rule set `I`). The enforced order is:

1. Standard library
2. Third-party packages (Django, DRF, etc.)
3. Local application imports (`apps.*`, `core.*`, `config.*`)

Blank line between each group. Ruff auto-fixes on `ruff check --fix` or `ruff format`.
