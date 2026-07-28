from django.urls import path

from . import views

app_name = "mfa"

urlpatterns = [
    path("setup/", views.MFASetupView.as_view(), name="setup"),
    path("confirm-setup/", views.MFAConfirmSetupView.as_view(), name="confirm-setup"),
    path("verify/", views.MFAVerifyView.as_view(), name="verify"),
    path("disable/", views.MFADisableView.as_view(), name="disable"),
    path("backup-codes/", views.MFABackupCodesView.as_view(), name="backup-codes"),
    path("status/", views.MFAStatusView.as_view(), name="status"),
    path("login-verify/", views.MFALoginVerifyView.as_view(), name="login-verify"),
]
