# Management Commands

How to write management commands in this project — from structure and naming to output conventions and error handling.

---

## Overview

Management commands are CLI tools invoked via `uv run python manage.py <command>`. They serve operational and development-time purposes: validation checks, data seeding, maintenance tasks.

Each app can define its own commands. Cross-cutting platform commands live in their respective `sys_` app.

---

## Structure

Commands follow Django's standard layout:

```
apps/<app_name>/
└── management/
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── <verb>_<noun>.py
```

Every command inherits from the project's `BaseCommand`:

```python
from core.base.commands import BaseCommand


class Command(BaseCommand):
    """Validate all permission catalog files."""

    help = "Validate all permission catalog files across apps."

    def handle(self, *args, **options):
        errors = self.run_validation()
        if errors:
            for err in errors:
                self.error(err)
            self.summary_failure(f"{len(errors)} error(s) found.")
        else:
            self.summary_success("All catalogs valid.")
```

---

## BaseCommand

Located at `core/base/commands.py`. Wraps Django's `BaseCommand` with a Rich `Console` for styled output.

### Helpers

| Method | Purpose |
|--------|---------|
| `self.success(msg)` | Print a success message (green) |
| `self.error(msg)` | Print an error message (red) |
| `self.warning(msg)` | Print a warning message (yellow) |
| `self.summary_success(msg)` | Print a final success summary and exit 0 |
| `self.summary_failure(msg)` | Print a final failure summary and exit 1 |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error |

---

## Naming Convention

Commands use `verb_noun` format:

```
check_permission_catalog
seed_default_roles
sync_tenant_settings
```

- The verb describes the action
- The noun describes the target
- Use snake_case (Django convention)

---

## Output

- Use Rich via `BaseCommand` helpers for all terminal output
- Always end with a summary line (via `summary_success` or `summary_failure`)
- Do not use `print()` directly — use `self.success()`, `self.error()`, `self.warning()`

---

## Logging

- Command output (what the user sees in terminal) goes through Rich via stdout
- Application-level side effects (DB writes, external calls) go through Python `logging` as any other code path would
- Pure validation commands (no side effects) do not log — stdout only

---

## CI Integration

Validation commands run in CI alongside other quality checks:

```yaml
- name: Check permission catalog
  run: uv run python manage.py check_permission_catalog
```

Locally:

```bash
uv run python manage.py check_permission_catalog
```

They must exit with code `1` on failure so CI fails the pipeline.

---

## Common Pitfalls

| Pitfall | Problem | Solution |
|---------|---------|----------|
| Using `print()` | Bypasses Rich styling and testability | Use `self.success()`, `self.error()`, `self.warning()` |
| Missing `help` attribute | `manage.py help` shows no description | Always set `help` on the command class |
| Swallowing exceptions | Command exits 0 on failure, CI passes | Use `self.summary_failure()` which exits with code 1 |
| Mixing output and logging | Confusing terminal output | Stdout for user-facing output, `logging` for side effects only |

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Validation/linting of config files | Command with `check_` prefix, runs in CI |
| Command belongs to a specific domain | Place in that app's `management/commands/` |
| Command is cross-cutting infrastructure | Place in the relevant `sys_` app |
