from django.apps import AppConfig


class IamMfaConfig(AppConfig):
    name = "apps.iam_mfa"
    label = "iam_mfa"
    verbose_name = "IAM MFA"

    def ready(self) -> None:
        import apps.iam_mfa.signals  # noqa: F401
