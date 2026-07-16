"""Tests for the permission catalog loader, merger, and validator."""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from apps.sys_permissions.catalog import (
    _generate_default_catalog,
    _merge_catalog,
    build_effective_catalogs,
    get_default_role_permissions,
    get_merged_catalog,
    validate_all,
    validate_business_rules,
    validate_schema,
    validate_uniqueness,
)


class TestGenerateDefaultCatalog:
    def test_generates_crud_actions(self) -> None:
        catalog = _generate_default_catalog("invoices")
        actions = catalog["resources"]["invoices"]["actions"]
        assert set(actions.keys()) == {"view", "create", "update", "delete"}

    def test_view_is_readonly(self) -> None:
        catalog = _generate_default_catalog("invoices")
        view = catalog["resources"]["invoices"]["actions"]["view"]
        assert view["readonly"] is True

    def test_write_actions_not_readonly(self) -> None:
        catalog = _generate_default_catalog("invoices")
        actions = catalog["resources"]["invoices"]["actions"]
        for action_name in ("create", "update", "delete"):
            assert actions[action_name]["readonly"] is False

    def test_view_granted_to_all_roles(self) -> None:
        catalog = _generate_default_catalog("invoices")
        view = catalog["resources"]["invoices"]["actions"]["view"]
        assert view["default_roles"] == {"owner": 1, "admin": 1, "member": 1, "viewer": 1}

    def test_write_actions_granted_to_owner_admin_only(self) -> None:
        catalog = _generate_default_catalog("invoices")
        actions = catalog["resources"]["invoices"]["actions"]
        for action_name in ("create", "update", "delete"):
            assert actions[action_name]["default_roles"] == {
                "owner": 1, "admin": 1, "member": 0, "viewer": 0
            }

    def test_label_derived_from_app_label(self) -> None:
        catalog = _generate_default_catalog("invoices")
        assert catalog["resources"]["invoices"]["label"] == "Invoices"


class TestMergeCatalog:
    def test_resources_false_disables_all(self) -> None:
        defaults = _generate_default_catalog("tenants")
        explicit: dict[str, Any] = {"resources": False}
        merged = _merge_catalog(defaults, explicit)
        assert merged["resources"] == {}

    def test_resource_false_removes_resource(self) -> None:
        defaults = _generate_default_catalog("tenants")
        explicit: dict[str, Any] = {"resources": {"tenants": False}}
        merged = _merge_catalog(defaults, explicit)
        assert "tenants" not in merged["resources"]

    def test_action_false_removes_action(self) -> None:
        defaults = _generate_default_catalog("tenants")
        explicit: dict[str, Any] = {
            "resources": {"tenants": {"label": "Tenants", "actions": {"create": False}}}
        }
        merged = _merge_catalog(defaults, explicit)
        assert "create" not in merged["resources"]["tenants"]["actions"]
        assert "view" in merged["resources"]["tenants"]["actions"]

    def test_explicit_action_overrides_default(self) -> None:
        defaults = _generate_default_catalog("tenants")
        custom_view = {
            "label": "Custom view",
            "readonly": True,
            "default_roles": {"owner": 1, "admin": 1, "member": 0, "viewer": 0},
        }
        explicit: dict[str, Any] = {
            "resources": {"tenants": {"label": "Tenants", "actions": {"view": custom_view}}}
        }
        merged = _merge_catalog(defaults, explicit)
        assert merged["resources"]["tenants"]["actions"]["view"] == custom_view

    def test_custom_action_added_on_top_of_defaults(self) -> None:
        defaults = _generate_default_catalog("tenants")
        invite_action = {
            "label": "Invite",
            "readonly": False,
            "default_roles": {"owner": 1, "admin": 1, "member": 0, "viewer": 0},
        }
        explicit: dict[str, Any] = {
            "resources": {"tenants": {"label": "Tenants", "actions": {"invite": invite_action}}}
        }
        merged = _merge_catalog(defaults, explicit)
        assert "invite" in merged["resources"]["tenants"]["actions"]
        assert "view" in merged["resources"]["tenants"]["actions"]

    def test_custom_resource_gets_crud_defaults(self) -> None:
        defaults = _generate_default_catalog("tenants")
        explicit: dict[str, Any] = {
            "resources": {"teams": {"label": "Teams"}}
        }
        merged = _merge_catalog(defaults, explicit)
        assert "teams" in merged["resources"]
        assert set(merged["resources"]["teams"]["actions"].keys()) == {
            "view", "create", "update", "delete"
        }

    def test_custom_resource_with_disabled_actions(self) -> None:
        defaults = _generate_default_catalog("tenants")
        explicit: dict[str, Any] = {
            "resources": {
                "members": {
                    "label": "Members",
                    "actions": {"create": False, "update": False, "delete": False},
                }
            }
        }
        merged = _merge_catalog(defaults, explicit)
        assert set(merged["resources"]["members"]["actions"].keys()) == {"view"}

    def test_explicit_label_overrides_default(self) -> None:
        defaults = _generate_default_catalog("tenants")
        explicit: dict[str, Any] = {
            "resources": {"tenants": {"label": "Organizations"}}
        }
        merged = _merge_catalog(defaults, explicit)
        assert merged["resources"]["tenants"]["label"] == "Organizations"

    def test_no_explicit_keeps_defaults(self) -> None:
        defaults = _generate_default_catalog("tenants")
        explicit: dict[str, Any] = {"resources": {}}
        merged = _merge_catalog(defaults, explicit)
        assert "tenants" in merged["resources"]
        assert set(merged["resources"]["tenants"]["actions"].keys()) == {
            "view", "create", "update", "delete"
        }


class TestValidateSchema:
    def test_valid_catalog_passes(self) -> None:
        catalog: dict[str, Any] = {
            "resources": {
                "items": {
                    "label": "Items",
                    "actions": {
                        "view": {
                            "label": "View items",
                            "readonly": True,
                            "default_roles": {"owner": 1, "admin": 1, "member": 1, "viewer": 1},
                        }
                    },
                }
            }
        }
        errors = validate_schema(catalog, "test_app")
        assert errors == []

    def test_resources_false_passes(self) -> None:
        catalog: dict[str, Any] = {"resources": False}
        errors = validate_schema(catalog, "test_app")
        assert errors == []

    def test_resource_false_passes(self) -> None:
        catalog: dict[str, Any] = {"resources": {"items": False}}
        errors = validate_schema(catalog, "test_app")
        assert errors == []

    def test_action_false_passes(self) -> None:
        catalog: dict[str, Any] = {
            "resources": {"items": {"label": "Items", "actions": {"create": False}}}
        }
        errors = validate_schema(catalog, "test_app")
        assert errors == []

    def test_missing_resources_key_fails(self) -> None:
        catalog: dict[str, Any] = {}
        errors = validate_schema(catalog, "test_app")
        assert len(errors) > 0

    def test_invalid_role_value_fails(self) -> None:
        catalog: dict[str, Any] = {
            "resources": {
                "items": {
                    "label": "Items",
                    "actions": {
                        "view": {
                            "label": "View",
                            "readonly": True,
                            "default_roles": {"owner": 2, "admin": 1, "member": 1, "viewer": 1},
                        }
                    },
                }
            }
        }
        errors = validate_schema(catalog, "test_app")
        assert len(errors) > 0


class TestValidateBusinessRules:
    def test_viewer_with_write_permission_fails(self) -> None:
        catalog: dict[str, Any] = {
            "resources": {
                "items": {
                    "label": "Items",
                    "actions": {
                        "create": {
                            "label": "Create",
                            "readonly": False,
                            "default_roles": {"owner": 1, "admin": 1, "member": 0, "viewer": 1},
                        }
                    },
                }
            }
        }
        errors = validate_business_rules(catalog, "test_app")
        assert len(errors) == 1
        assert "viewer" in errors[0].lower()

    def test_viewer_with_readonly_permission_passes(self) -> None:
        catalog: dict[str, Any] = {
            "resources": {
                "items": {
                    "label": "Items",
                    "actions": {
                        "view": {
                            "label": "View",
                            "readonly": True,
                            "default_roles": {"owner": 1, "admin": 1, "member": 1, "viewer": 1},
                        }
                    },
                }
            }
        }
        errors = validate_business_rules(catalog, "test_app")
        assert errors == []

    def test_resources_false_passes(self) -> None:
        catalog: dict[str, Any] = {"resources": False}
        errors = validate_business_rules(catalog, "test_app")
        assert errors == []

    def test_resource_false_skipped(self) -> None:
        catalog: dict[str, Any] = {"resources": {"items": False}}
        errors = validate_business_rules(catalog, "test_app")
        assert errors == []


class TestValidateUniqueness:
    def test_unique_codenames_pass(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            ("app_a", {"resources": {"items": {"actions": {"view": {}}}}}),
            ("app_b", {"resources": {"orders": {"actions": {"view": {}}}}}),
        ]
        errors = validate_uniqueness(catalogs)
        assert errors == []

    def test_duplicate_codenames_fail(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            ("app_a", {"resources": {"items": {"actions": {"view": {}}}}}),
            ("app_a", {"resources": {"items": {"actions": {"view": {}}}}}),
        ]
        errors = validate_uniqueness(catalogs)
        assert len(errors) == 1
        assert "app_a.items.view" in errors[0]

    def test_resources_false_skipped(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            ("app_a", {"resources": False}),
            ("app_b", {"resources": {"items": {"actions": {"view": {}}}}}),
        ]
        errors = validate_uniqueness(catalogs)
        assert errors == []


class TestValidateAll:
    def test_valid_project_catalogs_pass(self) -> None:
        errors = validate_all()
        assert errors == []


class TestGetMergedCatalog:
    def test_returns_all_codenames(self) -> None:
        merged = get_merged_catalog()
        assert "tenants.access" in merged
        assert "tenants.tenants.view" in merged
        assert "tenants.tenants.update" in merged
        assert "iam_teams.teams.view" in merged
        assert "iam_users.access" in merged
        assert "iam_users.members.view" in merged
        assert "iam_users.members.invite" in merged
        assert "iam_roles.roles.view" in merged

    def test_disabled_actions_not_present(self) -> None:
        merged = get_merged_catalog()
        assert "tenants.tenants.create" not in merged
        assert "tenants.tenants.delete" not in merged

    def test_disabled_resources_not_present(self) -> None:
        merged = get_merged_catalog()
        # iam_auth app has resources: false but still has access
        assert "iam_auth.iam_auth.view" not in merged
        assert "iam_auth.access" in merged


class TestGetDefaultRolePermissions:
    def test_returns_dict_per_role(self) -> None:
        perms = get_default_role_permissions()
        assert set(perms.keys()) == {"owner", "admin", "member", "viewer"}

    def test_values_are_dicts_with_int_values(self) -> None:
        perms = get_default_role_permissions()
        for role, role_perms in perms.items():
            assert isinstance(role_perms, dict)
            for codename, value in role_perms.items():
                assert value == 1, f"{role}.{codename} should be 1"

    def test_viewer_only_has_readonly_permissions(self) -> None:
        merged = get_merged_catalog()
        perms = get_default_role_permissions()
        for codename in perms["viewer"]:
            assert merged[codename]["readonly"] is True, (
                f"Viewer has non-readonly permission: {codename}"
            )

    def test_owner_has_all_permissions(self) -> None:
        merged = get_merged_catalog()
        perms = get_default_role_permissions()
        assert set(perms["owner"].keys()) == set(merged.keys())
