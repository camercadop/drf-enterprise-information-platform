"""Handler registry — maps event types to their registered handler callables."""

import importlib
import logging
from collections import defaultdict
from collections.abc import Callable

from apps.sys_eventbus.envelope import EventEnvelope

logger = logging.getLogger(__name__)

HandlerFn = Callable[[EventEnvelope], None]

_registry: dict[str, list[HandlerFn]] = defaultdict(list)


def event_handler(event_type: str) -> Callable[[HandlerFn], HandlerFn]:
    """Register a callable as a handler for the given event type.

    Decorate any function with this to subscribe it to an event type on the
    bus. The function must accept a single ``EventEnvelope`` argument and
    return ``None``. Exceptions raised by the handler propagate to the
    consumer, which applies retry and DLQ logic.

    Use this decorator in an app's ``event_handlers.py`` — the file is auto-imported
    by ``SysEventBusConfig.ready()`` so no manual wiring is needed.

    Args:
        event_type: Dot-namespaced event type string (e.g. ``"document.created"``).

    Returns:
        The original function, unmodified.
    """

    def decorator(fn: HandlerFn) -> HandlerFn:
        _registry[event_type].append(fn)
        logger.info(
            "Event handler registered event_type=%s handler=%s",
            event_type,
            fn.__qualname__,
        )
        return fn

    return decorator


def get_handlers(event_type: str) -> list[HandlerFn]:
    """Return all registered handlers for the given event type.

    Called by the consumer to dispatch an incoming message. Returns an empty
    list if no handlers are registered — the consumer logs a warning and
    acknowledges the message without processing.

    Args:
        event_type: Dot-namespaced event type string (e.g. ``"document.created"``).

    Returns:
        List of handler callables. May be empty.
    """
    return list(_registry[event_type])


def autodiscover_handlers() -> None:
    """Import ``handlers.py`` from every installed app that defines one.

    Called from ``SysEventBusConfig.ready()``. Triggers decorator-based
    registration by importing each app's ``event_handlers`` module. Apps that do
    not have an ``event_handlers.py`` are silently skipped.
    """
    from django.apps import apps

    for app_config in apps.get_app_configs():
        module_path = f"{app_config.name}.event_handlers"
        try:
            importlib.import_module(module_path)
            logger.info("Event handlers autodiscovered app=%s", app_config.name)
        except ModuleNotFoundError:
            pass
        except Exception:
            logger.warning(
                "Failed to import event_handlers app=%s module=%s",
                app_config.name,
                module_path,
                exc_info=True,
            )
