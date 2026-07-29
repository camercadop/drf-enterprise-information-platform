from django.urls import path

from . import views

app_name = "iam_oauth"

urlpatterns = [
    path("authorize/", views.AuthorizeView.as_view(), name="authorize"),
    path("token/", views.TokenView.as_view(), name="token"),
    path("revoke/", views.RevokeView.as_view(), name="revoke"),
]
