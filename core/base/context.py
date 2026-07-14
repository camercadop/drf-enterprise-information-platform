"""Boundary scope context for request-scoped data isolation.

Stores the active boundary scope (e.g., tenant_id) in a ContextVar so that
ORM-level managers can enforce data isolation independently of the view layer.
"""

from contextvars import ContextVar, Token
from typing import Any

_scope_var: ContextVar[dict[str, Any] | None] = ContextVar("_scope_var", default=None)


def bind_scope(scope: dict[str, Any]) -> Token[dict[str, Any] | None]:
    """Bind boundary scope values for the current context.

    Args:
        scope: Mapping of field names to values (e.g., {"tenant_id": "uuid"}).

    Returns:
        Token that can be used to reset the scope.
    """
    return _scope_var.set(scope)


def get_bound_scope() -> dict[str, Any]:
    """Return the currently bound scope, or an empty dict if unbound."""
    return _scope_var.get() or {}


def unbind_scope(token: Token[dict[str, Any] | None]) -> None:
    """Reset the scope to its previous state using the token from bind_scope.

    Args:
        token: The token returned by a prior bind_scope call.
    """
    _scope_var.reset(token)
