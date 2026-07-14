"""Django app configuration for sys_health."""

from django.apps import AppConfig


class SysHealthConfig(AppConfig):
    """Operational health check endpoints for orchestrator probes."""

    name = "apps.sys_health"
    verbose_name = "System Health"
