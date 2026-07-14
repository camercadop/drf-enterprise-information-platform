"""App configuration for sys_audit."""

from django.apps import AppConfig


class SysAuditConfig(AppConfig):
    """System audit trail application."""

    name = "apps.sys_audit"
    verbose_name = "System Audit"
