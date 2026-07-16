"""Unit tests for the tenant settings catalog engine."""

from typing import Any
from unittest.mock import patch

from apps.tenant_settings.catalog import (
    validate_type_schema_consistency,
    validate_uniqueness,
)


class TestValidateUniqueness:
    def test_no_duplicates_returns_no_errors(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            ("app_a", {"settings": {"key_a": {}}}),
            ("app_b", {"settings": {"key_b": {}}}),
        ]
        assert validate_uniqueness(catalogs) == []

    def test_duplicate_key_across_apps_returns_error(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            ("app_a", {"settings": {"shared_key": {}}}),
            ("app_b", {"settings": {"shared_key": {}}}),
        ]
        errors = validate_uniqueness(catalogs)
        assert len(errors) == 1
        assert "shared_key" in errors[0]
        assert "app_a" in errors[0]
        assert "app_b" in errors[0]

    def test_empty_catalogs_returns_no_errors(self) -> None:
        assert validate_uniqueness([]) == []


class TestValidateTypeSchemConsistency:
    def test_matching_type_and_schema_type_returns_no_errors(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            (
                "app_a",
                {
                    "settings": {
                        "my_int": {
                            "type": "integer",
                            "schema": {"type": "integer", "minimum": 1},
                        }
                    }
                },
            )
        ]
        assert validate_type_schema_consistency(catalogs) == []

    def test_conflicting_type_and_schema_type_returns_error(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            (
                "app_a",
                {
                    "settings": {
                        "bad_key": {
                            "type": "integer",
                            "schema": {"type": "string"},
                        }
                    }
                },
            )
        ]
        errors = validate_type_schema_consistency(catalogs)
        assert len(errors) == 1
        assert "bad_key" in errors[0]
        assert "integer" in errors[0]
        assert "string" in errors[0]

    def test_json_type_with_any_schema_type_returns_no_errors(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            (
                "app_a",
                {
                    "settings": {
                        "policy": {
                            "type": "json",
                            "schema": {"type": "object"},
                        }
                    }
                },
            )
        ]
        assert validate_type_schema_consistency(catalogs) == []

    def test_no_schema_field_skips_check(self) -> None:
        catalogs: list[tuple[str, dict[str, Any]]] = [
            ("app_a", {"settings": {"simple_key": {"type": "string"}}})
        ]
        assert validate_type_schema_consistency(catalogs) == []


class TestGetMergedCatalogCache:
    def test_catalog_is_cached_after_first_call(self) -> None:
        import apps.tenant_settings.catalog as catalog_module

        catalog_module._CATALOG_CACHE = None
        with patch.object(
            catalog_module, "discover_catalogs", return_value=[]
        ) as mock_discover:
            catalog_module.get_merged_catalog()
            catalog_module.get_merged_catalog()
            assert mock_discover.call_count == 1

    def test_cache_reset_triggers_reload(self) -> None:
        import apps.tenant_settings.catalog as catalog_module

        catalog_module._CATALOG_CACHE = None
        with patch.object(
            catalog_module, "discover_catalogs", return_value=[]
        ) as mock_discover:
            catalog_module.get_merged_catalog()
            catalog_module._CATALOG_CACHE = None
            catalog_module.get_merged_catalog()
            assert mock_discover.call_count == 2
