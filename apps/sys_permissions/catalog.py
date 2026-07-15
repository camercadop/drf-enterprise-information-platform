"""Permission catalog loader, merger, and validator.

Discovers permissions.json files from all installed apps, generates default
CRUD permissions for domain apps, merges explicit catalogs with defaults,
validates against JSON Schema and business rules, and provides an indexed
registry of all permissions.
"""

import json
from pathlib import Path
from typing import Any

import jsonschema
from django.apps import apps

SCHEMA_PATH = Path(__file__).parent / "permissions_schema.json"
CATALOG_FILENAME = "permissions.json"
DEFAULT_ROLES = ("owner", "admin", "member", "viewer")
VIEWER_ROLE = "viewer"
DOMAIN_APP_PREFIX = "apps."
SYSTEM_APP_PREFIX = "sys_"

ACCESS_ACTION: dict[str, Any] = {
    "label": "Access",
    "readonly": True,
    "default_roles": {"owner": 1, "admin": 1, "member": 1, "viewer": 1},
}

DEFAULT_CRUD_ACTIONS: dict[str, dict[str, Any]] = {
    "view": {
        "label": "View",
        "readonly": True,
        "default_roles": {"owner": 1, "admin": 1, "member": 1, "viewer": 1},
    },
    "create": {
        "label": "Create",
        "readonly": False,
        "default_roles": {"owner": 1, "admin": 1, "member": 0, "viewer": 0},
    },
    "update": {
        "label": "Update",
        "readonly": False,
        "default_roles": {"owner": 1, "admin": 1, "member": 0, "viewer": 0},
    },
    "delete": {
        "label": "Delete",
        "readonly": False,
        "default_roles": {"owner": 1, "admin": 1, "member": 0, "viewer": 0},
    },
}


def _load_schema() -> dict[str, Any]:
    """Load the JSON Schema for permission catalogs."""
    return json.loads(SCHEMA_PATH.read_text())  # type: ignore[no-any-return]


def _is_domain_app(app_config: Any) -> bool:
    """Check if an app is a domain app (not system-level, not third-party)."""
    name: str = app_config.name
    if not name.startswith(DOMAIN_APP_PREFIX):
        return False
    app_label: str = app_config.label
    if app_label.startswith(SYSTEM_APP_PREFIX):
        return False
    return True


def _generate_default_catalog(app_label: str) -> dict[str, Any]:
    """Generate default CRUD permissions for a domain app.

    Args:
        app_label: The app's label used as resource name.

    Returns:
        A catalog dict with default CRUD actions.
    """
    label = app_label.replace("_", " ").capitalize()
    actions = {}
    for action_name, action_def in DEFAULT_CRUD_ACTIONS.items():
        actions[action_name] = {
            "label": f"{action_def['label']} {label.lower()}",
            "readonly": action_def["readonly"],
            "default_roles": dict(action_def["default_roles"]),
        }
    return {
        "access": {
            "label": f"Access {label.lower()}",
            "readonly": ACCESS_ACTION["readonly"],
            "default_roles": dict(ACCESS_ACTION["default_roles"]),
        },
        "resources": {
            app_label: {
                "label": label,
                "actions": actions,
            }
        },
    }


def _merge_catalog(
    defaults: dict[str, Any], explicit: dict[str, Any]
) -> dict[str, Any]:
    """Merge an explicit catalog with generated defaults.

    Rules:
        - {"access": false} → removes the access permission
        - {"resources": false} → disables all resources (empty result)
        - {"resources": {"name": false}} → removes that resource
        - {"resources": {"name": {"actions": {"act": false}}}} → removes that action
        - Explicit actions override defaults
        - Custom actions are added on top of defaults

    Args:
        defaults: Auto-generated CRUD catalog for the app.
        explicit: The app's permissions.json content.

    Returns:
        Merged catalog with false values resolved.
    """
    # Merge access permission
    access = defaults.get("access")
    if "access" in explicit:
        explicit_access = explicit["access"]
        if explicit_access is False:
            access = None
        elif isinstance(explicit_access, dict):
            access = explicit_access

    resources_value = explicit.get("resources")

    if resources_value is False:
        result: dict[str, Any] = {"resources": {}}
        if access:
            result["access"] = access
        return result

    default_resources: dict[str, Any] = defaults.get("resources", {})
    explicit_resources: dict[str, Any] = resources_value if resources_value else {}

    merged_resources: dict[str, Any] = {}

    # Start with defaults
    for resource_name, resource_def in default_resources.items():
        if resource_name in explicit_resources:
            explicit_resource = explicit_resources[resource_name]
            if explicit_resource is False:
                continue
            # Merge actions
            merged_actions = dict(resource_def.get("actions", {}))
            explicit_actions = explicit_resource.get("actions", {})
            for action_name, action_def in explicit_actions.items():
                if action_def is False:
                    merged_actions.pop(action_name, None)
                else:
                    merged_actions[action_name] = action_def
            merged_resources[resource_name] = {
                "label": explicit_resource.get("label", resource_def["label"]),
                "actions": merged_actions,
            }
        else:
            merged_resources[resource_name] = resource_def

    # Add explicit resources not in defaults
    for resource_name, resource_def in explicit_resources.items():
        if resource_name not in default_resources:
            if resource_def is False:
                continue
            # Generate CRUD defaults for this resource, then merge explicit actions
            label = resource_def.get("label", resource_name.capitalize())
            base_actions: dict[str, Any] = {}
            for action_name, action_def in DEFAULT_CRUD_ACTIONS.items():
                base_actions[action_name] = {
                    "label": f"{action_def['label']} {label.lower()}",
                    "readonly": action_def["readonly"],
                    "default_roles": dict(action_def["default_roles"]),
                }
            # Override/remove with explicit actions
            for action_name, action_def in resource_def.get("actions", {}).items():
                if action_def is False:
                    base_actions.pop(action_name, None)
                else:
                    base_actions[action_name] = action_def
            if base_actions:
                merged_resources[resource_name] = {
                    "label": label,
                    "actions": base_actions,
                }

    result = {"resources": merged_resources}
    if access:
        result["access"] = access
    return result


def discover_domain_apps() -> list[Any]:
    """Find all domain apps (non-system, non-third-party)."""
    return [cfg for cfg in apps.get_app_configs() if _is_domain_app(cfg)]


def discover_catalogs() -> list[tuple[str, Path]]:
    """Find all permissions.json files in installed apps.

    Returns:
        List of (app_label, path) tuples for each catalog found.
    """
    catalogs: list[tuple[str, Path]] = []
    for app_config in apps.get_app_configs():
        catalog_path = Path(app_config.path) / CATALOG_FILENAME
        if catalog_path.exists():
            catalogs.append((app_config.label, catalog_path))
    return catalogs


def load_catalog(path: Path) -> dict[str, Any]:
    """Load and parse a single permissions.json file."""
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def build_effective_catalogs() -> list[tuple[str, dict[str, Any]]]:
    """Build effective catalogs for all domain apps.

    For each domain app:
    - Generate default CRUD permissions
    - If permissions.json exists, merge it with defaults
    - If no permissions.json, use defaults as-is

    Returns:
        List of (app_label, effective_catalog) tuples.
    """
    domain_apps = discover_domain_apps()
    effective: list[tuple[str, dict[str, Any]]] = []

    for app_config in domain_apps:
        app_label: str = app_config.label
        defaults = _generate_default_catalog(app_label)
        catalog_path = Path(app_config.path) / CATALOG_FILENAME

        if catalog_path.exists():
            explicit = load_catalog(catalog_path)
            merged = _merge_catalog(defaults, explicit)
        else:
            merged = defaults

        effective.append((app_label, merged))

    return effective


def validate_schema(catalog: dict[str, Any], app_label: str) -> list[str]:
    """Validate a catalog against the JSON Schema.

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


def validate_business_rules(catalog: dict[str, Any], app_label: str) -> list[str]:
    """Validate business rules beyond schema structure.

    Rules:
        - Viewer roles cannot have 1 on readonly=false permissions.

    Returns:
        List of error messages. Empty if valid.
    """
    errors: list[str] = []
    resources = catalog.get("resources")
    if not resources or resources is False:
        return errors

    for resource_name, resource in resources.items():
        if resource is False:
            continue
        for action_name, action in resource.get("actions", {}).items():
            if action is False:
                continue
            if (
                not action.get("readonly")
                and action.get("default_roles", {}).get(VIEWER_ROLE) == 1
            ):
                codename = f"{app_label}.{resource_name}.{action_name}"
                errors.append(
                    f"[{app_label}] Viewer role cannot have write permission:"
                    f" {codename}"
                )
    return errors


def validate_uniqueness(catalogs: list[tuple[str, dict[str, Any]]]) -> list[str]:
    """Validate that codenames are unique across all apps.

    Returns:
        List of error messages. Empty if valid.
    """
    seen: dict[str, str] = {}
    errors: list[str] = []
    for app_label, catalog in catalogs:
        # Check access permission
        access = catalog.get("access")
        if access and access is not False:
            codename = f"{app_label}.access"
            if codename in seen:
                errors.append(
                    f"Duplicate codename '{codename}' in [{app_label}] "
                    f"(already defined in [{seen[codename]}])"
                )
            else:
                seen[codename] = app_label
        # Check resource permissions
        resources = catalog.get("resources")
        if not resources or resources is False:
            continue
        for resource_name, resource in resources.items():
            if resource is False:
                continue
            for action_name, action in resource.get("actions", {}).items():
                if action is False:
                    continue
                codename = f"{app_label}.{resource_name}.{action_name}"
                if codename in seen:
                    errors.append(
                        f"Duplicate codename '{codename}' in [{app_label}] "
                        f"(already defined in [{seen[codename]}])"
                    )
                else:
                    seen[codename] = app_label
    return errors


def validate_all() -> list[str]:
    """Run full validation on all permission catalogs.

    Validates explicit permissions.json files against the schema,
    then validates the effective (merged) catalogs for business rules
    and uniqueness.

    Returns:
        List of all error messages. Empty if everything is valid.
    """
    all_errors: list[str] = []

    # Validate explicit catalog files against schema
    for app_label, path in discover_catalogs():
        try:
            catalog = load_catalog(path)
        except json.JSONDecodeError as e:
            all_errors.append(f"[{app_label}] Invalid JSON: {e}")
            continue
        all_errors.extend(validate_schema(catalog, app_label))

    if all_errors:
        return all_errors

    # Build effective catalogs and validate business rules + uniqueness
    effective = build_effective_catalogs()
    for app_label, catalog in effective:
        all_errors.extend(validate_business_rules(catalog, app_label))
    all_errors.extend(validate_uniqueness(effective))

    return all_errors


def get_merged_catalog() -> dict[str, dict[str, Any]]:
    """Load and merge all catalogs into a single indexed registry.

    Returns:
        Dict mapping codename to action metadata, e.g.:
        {
            "tenants.tenants.view": {"label": "View tenants", "readonly": True, ...},
            ...
        }
    """
    effective = build_effective_catalogs()
    merged: dict[str, dict[str, Any]] = {}
    for app_label, catalog in effective:
        # Include access permission
        access = catalog.get("access")
        if access and access is not False:
            codename = f"{app_label}.access"
            merged[codename] = access
        # Include resource permissions
        resources = catalog.get("resources")
        if not resources or resources is False:
            continue
        for resource_name, resource in resources.items():
            if resource is False:
                continue
            for action_name, action in resource.get("actions", {}).items():
                if action is False:
                    continue
                codename = f"{app_label}.{resource_name}.{action_name}"
                merged[codename] = action
    return merged


def get_default_role_permissions() -> dict[str, dict[str, int]]:
    """Build the default permission set for each role from all catalogs.

    Returns:
        Dict mapping role name to a dict of codename→value, e.g.:
        {"owner": {"tenants.tenants.view": 1, ...}, "viewer": {"tenants.tenants.view": 1}}
    """
    merged = get_merged_catalog()
    role_permissions: dict[str, dict[str, int]] = {role: {} for role in DEFAULT_ROLES}
    for codename, action in merged.items():
        for role in DEFAULT_ROLES:
            value = action.get("default_roles", {}).get(role, 0)
            if value == 1:
                role_permissions[role][codename] = 1
    return role_permissions
