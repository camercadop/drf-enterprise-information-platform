# Code Style

How the code should look — formatting, structure, naming, and structural conventions. This file is the single source of truth for style decisions.

---

## Type Safety

- All function parameters must have type annotations
- Use `X | None` instead of `Optional[X]`
- Avoid returning untyped values from typed functions

## Naming

- Files: lowercase with underscores (`base_serializer.py`)
- Classes: PascalCase (`BaseSerializer`)
- Plugins: PascalCase ending in `Plugin` (`SoftDeletablePlugin`)
- Template hooks: `pre_*`, `do_*`, `post_*`
- Plugin hooks: `on_pre_*`, `on_post_*`, `on_*`

## Models

- All tenant-scoped models inherit from `TenantAwareModel` (includes timestamps + soft-delete + tenant FK)
- Use `BaseModel` for platform-level models that don't belong to a tenant
- All models use UUID as primary key (`primary_key=True`)
- Do not set `default_auto_field` in app configs
- Add a comment under each field explaining its purpose
- Soft-delete fields: `deleted_at`, `deleted_by`
- Timestamp fields: `created_at`, `updated_at`
- Separate each field + comment pair with one blank line

## Serializers

- Inherit from `BaseSerializer`
- Use plugins for cross-cutting concerns
- Use template methods for per-serializer customization
- Annotate `validated_data` as `dict[str, Any]`

## Views

- Inherit from `BaseViewSet` for CRUD resources
- Use `APIView` for single-action endpoints (login, logout, password change)
- Use `serializer_classes` dict for per-action serializer mapping instead of overriding `get_serializer_class`
- Use `write_permission_classes` for elevated write permissions instead of overriding `get_permissions`
- Lifecycle hooks: `pre_create`/`post_create`, `pre_update`/`post_update`, `pre_destroy`/`post_destroy`
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

## Import Ordering

Managed by Ruff (`isort` rules, rule set `I`). The enforced order is:

1. Standard library
2. Third-party packages (Django, DRF, etc.)
3. Local application imports (`apps.*`, `core.*`, `config.*`)

Blank line between each group. Ruff auto-fixes on `ruff check --fix` or `ruff format`.
