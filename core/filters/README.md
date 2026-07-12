# Filters

Shared filter backends and filtersets for the enterprise platform.

## Filter Backends (DRF)

Registered globally via `REST_FRAMEWORK["DEFAULT_FILTER_BACKENDS"]` in settings. Apply to all views automatically.

### SoftDeleteFilterBackend

Excludes soft-deleted records (where `deleted_at` is not null) from querysets by default. Pass `?include_deleted=true` to include them.

- No-op if the model has no `deleted_at` field.

### TenantFilterBackend

Lives in `apps/tenants/filters.py` (owned by the tenants domain). See `apps/tenants/README.md` for full documentation.

## FilterSets (django-filters)

### BaseFilterSet

Abstract base providing common declared filters for all filtersets:

- `id`
- `created_at`
- `updated_at`

### SoftDeleteFilter

Abstract filterset with an `include_deleted` boolean filter for explicit soft-delete toggling.
