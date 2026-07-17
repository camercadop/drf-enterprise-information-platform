# Logging

How to add structured, consistent logging across domain modules — what to log, at which severity, and how to configure loggers correctly.

---

## Overview

The project uses Python's standard `logging` module. Each module declares its own logger using `logging.getLogger(__name__)`, which produces a logger name that mirrors the module path (e.g., `apps.iam_auth.views`). This allows log output to be filtered and routed per app in Django's `LOGGING` configuration.

Do not use `print()` for diagnostic output. Use the logger.

---

## Declaring a Logger

Every module that emits log output must declare a module-level logger:

```python
import logging

logger = logging.getLogger(__name__)
```

Place the import with other stdlib imports and the logger declaration immediately after all imports, before any class or function definitions.

---

## Severity Levels

| Level | When to use |
|-------|-------------|
| `logger.debug(...)` | Detailed internal state useful during development only. Never in production paths |
| `logger.info(...)` | Normal, expected events worth recording (successful login, logout, resource created) |
| `logger.warning(...)` | Security-relevant or unexpected events that do not cause a failure (failed login, IP blocked, permission denied) |
| `logger.error(...)` | Unhandled exceptions or failures that require attention. Use `exc_info=True` to attach the traceback |

---

## What to Log

### Always log

- Security enforcement decisions: permission denied, access blocked, policy violations (`warning`)
- Authentication and session events: login, logout, token operations (`info` on success, `warning` on failure)
- Privileged or destructive operations: account unlock, password change, membership changes, resource deletion (`info`)
- Unexpected but handled conditions: missing expected data, fallback paths taken (`warning`)
- Unhandled exceptions in exception handlers (`error`)

### Do not log

- Passwords, tokens, or secrets — never
- Full request bodies — they may contain credentials
- PII beyond what is strictly necessary for traceability (email is acceptable as an auth identifier; avoid names, phone numbers, addresses)
- Routine read operations (list, retrieve) — these produce noise without value

---

## Management Commands

Commands have two output channels that serve different purposes:

- **stdout (Rich)** — user-facing terminal output via `self.success()`, `self.error()`, `self.warning()`. Always present.
- **Python `logging`** — application-level events for observability. Only when the command has side effects.

Use `logging` in commands when:

- The command performs DB writes or external calls — log each significant operation (`info`)
- An expected but recoverable error occurs during processing — log with context (`warning`)
- An unhandled exception is caught — log with `exc_info=True` (`error`)

Do not use `logging` in pure validation commands (no side effects) — stdout only is sufficient.

See [Management Commands guideline](management-commands.md) for the full stdout vs logging split and `BaseCommand` helpers.

---

## Log Message Format

Use `%s`-style formatting — pass arguments to the logger, do not use f-strings. This defers string interpolation and avoids unnecessary work when the log level is disabled.

```python
# Correct
logger.warning("Login blocked: account locked email=%s", email)
logger.info("Login successful email=%s", email)
logger.warning("Login blocked: IP not allowed ip=%s tenant_id=%s", ip, tenant_id)

# Wrong — eager interpolation
logger.warning(f"Login blocked: account locked email={email}")
```

Include relevant context as `key=value` pairs in the message. This makes log lines grep-friendly and compatible with structured log parsers.

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Normal successful operation | `logger.info(...)` |
| Security enforcement triggered | `logger.warning(...)` |
| Unexpected exception caught | `logger.error(..., exc_info=True)` |
| Development-only diagnostic | `logger.debug(...)` |
| Logging a value that may be None | Guard with `or "unknown"` before passing to logger |
| Multiple context fields | Inline as `key=value` pairs in the message string |
