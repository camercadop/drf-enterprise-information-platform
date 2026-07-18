"""App configuration for sys_user_event."""

from django.apps import AppConfig


class SysUserEventConfig(AppConfig):
    """User event and authentication attempt tracking application."""

    name = "apps.sys_user_event"
    verbose_name = "System User Events"
