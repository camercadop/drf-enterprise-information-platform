"""Validate all tenant_settings.json catalog files across installed apps."""

from typing import Any

from apps.tenant_settings.catalog import discover_catalogs, validate_all
from core.base.commands import BaseCommand


class Command(BaseCommand):
    """Validate tenant_settings.json catalog files for schema and uniqueness."""

    help = "Validate all tenant_settings.json catalog files across installed apps."

    def handle(self, *args: Any, **options: Any) -> None:
        catalogs = discover_catalogs()
        if not catalogs:
            self.warning("No tenant settings catalogs found.")
            return

        self.console.print(
            f"Found {len(catalogs)} catalog(s): {', '.join(label for label, _ in catalogs)}"
        )

        errors = validate_all()
        if errors:
            for err in errors:
                self.error(f"  {err}")
            self.summary_failure(f"{len(errors)} error(s) found.")
        else:
            self.summary_success(f"All {len(catalogs)} catalog(s) valid.")
