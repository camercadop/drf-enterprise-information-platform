"""Tenant settings catalog loader and validator.

Discovers tenant_settings.json files from all installed apps, merges them
into a single registry, validates against JSON Schema and uniqueness rules,
and provides the indexed catalog used at runtime for key validation and
value coercion.
"""

import json
from pathlib import Path
from typing import Any

import jsonschema
from django.apps import apps

CATALOG_FILENAME = "tenant_settings.json"
SCHEMA_PATH = Path(__file__).parent / "catalog_schema.json"


def _load_schema() -> dict[str, Any]:
    """Load the JSON Schema for tenant_settings.json catalog files."""
    return json.loads(SCHEMA_PATH.read_text())  # type: ignore[no-any-return]


def discover_catalogs() -> list[tuple[str, Path]]:
    """Find all tenant_settings.json files across installed apps.

    Returns:
        List of (app_label, path) tuples for each catalog found.
    """
    catalogs: list[tuple[str, Path]] = []
    for app_config in apps.get_app_configs():
        path = Path(app_config.path) / CATALOG_FILENAME
        if path.exists():
            catalogs.append((app_config.label, path))
    return catalogs


def load_catalog(path: Path) -> dict[str, Any]:
    """Load and parse a single tenant_settings.json file."""
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def validate_schema(catalog: dict[str, Any], app_label: str) -> list[str]:
    """Validate a catalog against the JSON Schema.

    Args:
        catalog: Parsed catalog dict.
        app_label: App label used in error messages.

    Returns:
        List of error messages. Empty if valid.
    """
    schema = _load_schema()
    errors: list[str] = []
    for error in jsonschema.Draft7Validator(schema).iter_errors(catalog):
        errors.append(
            f"[{app_label}] Schema error at {error.json_path}: {error.message}"
        )
    return errors


TYPE_TO_SCHEMA_TYPE: dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "boolean": "boolean",
}
# json type is intentionally excluded — its schema.type is unconstrained.


def validate_type_schema_consistency(
    catalogs: list[tuple[str, dict[str, Any]]]
) -> list[str]:
    """Validate that type and schema.type are consistent within each entry.

    Rejects entries where the declared type maps to a known JSON Schema primitive
    but the schema declares a different top-level type. Entries with type=json
    are skipped — their schema.type is unconstrained by design.

    Args:
        catalogs: List of (app_label, catalog) tuples.

    Returns:
        List of error messages. Empty if valid.
    """
    errors: list[str] = []
    for app_label, catalog in catalogs:
        for key, entry in catalog.get("settings", {}).items():
            setting_type: str = entry.get("type", "")
            schema: dict[str, Any] | None = entry.get("schema")
            if not schema or setting_type not in TYPE_TO_SCHEMA_TYPE:
                continue
            schema_type: str | None = schema.get("type")
            expected = TYPE_TO_SCHEMA_TYPE[setting_type]
            if schema_type and schema_type != expected:
                errors.append(
                    f"[{app_label}] '{key}': type '{setting_type}' conflicts with "
                    f"schema.type '{schema_type}' (expected '{expected}')"
                )
    return errors


def validate_uniqueness(catalogs: list[tuple[str, dict[str, Any]]]) -> list[str]:
    """Validate that setting keys are unique across all apps.

    Args:
        catalogs: List of (app_label, catalog) tuples.

    Returns:
        List of error messages. Empty if valid.
    """
    seen: dict[str, str] = {}
    errors: list[str] = []
    for app_label, catalog in catalogs:
        for key in catalog.get("settings", {}):
            if key in seen:
                errors.append(
                    f"Duplicate setting key '{key}' in [{app_label}] "
                    f"(already defined in [{seen[key]}])"
                )
            else:
                seen[key] = app_label
    return errors


def validate_all() -> list[str]:
    """Run full validation on all tenant settings catalogs.

    Validates each tenant_settings.json against the schema, then checks
    for duplicate keys across all apps.

    Returns:
        List of all error messages. Empty if everything is valid.
    """
    all_errors: list[str] = []
    loaded: list[tuple[str, dict[str, Any]]] = []

    for app_label, path in discover_catalogs():
        try:
            catalog = load_catalog(path)
        except json.JSONDecodeError as e:
            all_errors.append(f"[{app_label}] Invalid JSON: {e}")
            continue
        schema_errors = validate_schema(catalog, app_label)
        all_errors.extend(schema_errors)
        if not schema_errors:
            loaded.append((app_label, catalog))

    if all_errors:
        return all_errors

    all_errors.extend(validate_uniqueness(loaded))
    all_errors.extend(validate_type_schema_consistency(loaded))
    return all_errors


_CATALOG_CACHE: dict[str, dict[str, Any]] | None = None
# Module-level cache for the merged catalog. Populated on first call and reused
# for the lifetime of the process. Invalidated only by a server restart.
# Future optimization: replace with Redis cache to support multi-process invalidation.


def get_merged_catalog() -> dict[str, dict[str, Any]]:
    """Load and merge all catalogs into a single indexed registry.

    Result is cached at module level after the first call. Private settings
    are included — callers are responsible for filtering them out when
    building API responses.

    Returns:
        Dict mapping setting key to its full definition, e.g.:
        {
            "password_policy": {
                "label": "Password policy",
                "namespace": "password",
                "type": "json",
                "default": "{}",
                "private": True,
                "schema": {...},
            },
        }
    """
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    merged: dict[str, dict[str, Any]] = {}
    for _app_label, path in discover_catalogs():
        catalog = load_catalog(path)
        for key, definition in catalog.get("settings", {}).items():
            merged[key] = definition
    _CATALOG_CACHE = merged
    return _CATALOG_CACHE
