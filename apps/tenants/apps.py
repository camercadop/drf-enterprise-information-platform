from django.apps import AppConfig


class TenantsConfig(AppConfig):
    name = "apps.tenants"
    verbose_name = "Tenants"

    def ready(self) -> None:
        import apps.tenants.signals  # noqa: F401
