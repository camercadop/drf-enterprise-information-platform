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

- All tenant-scoped models inherit from `BaseModel` (includes timestamps + soft-delete + tenant FK)
- Use `CoreModel` for platform-level models that don't belong to a tenant
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
