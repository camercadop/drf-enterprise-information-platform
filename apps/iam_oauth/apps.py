from django.apps import AppConfig


class IamOauthConfig(AppConfig):
    name = "apps.iam_oauth"
    label = "iam_oauth"
    verbose_name = "IAM OAuth2"

    def ready(self) -> None:
        import apps.iam_oauth.signals  # noqa: F401
