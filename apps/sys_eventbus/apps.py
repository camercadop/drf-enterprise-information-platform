"""App configuration for sys_eventbus."""

from django.apps import AppConfig


class SysEventBusConfig(AppConfig):
    """System event bus application."""

    name = "apps.sys_eventbus"
    verbose_name = "System Event Bus"

    def ready(self) -> None:
        """Auto-discover and register event handlers from all installed apps."""
        from apps.sys_eventbus.registry import autodiscover_handlers

        autodiscover_handlers()
