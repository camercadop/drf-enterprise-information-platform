from django.apps import AppConfig


class IamAuthConfig(AppConfig):
    name = "apps.iam_auth"
    label = "iam_auth"
    verbose_name = "IAM Authentication"

    def ready(self) -> None:
        import apps.iam_auth.signals  # noqa: F401
