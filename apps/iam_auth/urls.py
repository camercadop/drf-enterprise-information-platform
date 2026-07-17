from django.urls import path

from . import views

app_name = "authentication"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("logout-all/", views.LogoutAllView.as_view(), name="logout-all"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password-change"),
    path("unlock/<str:email>/", views.UnlockAccountView.as_view(), name="unlock-account"),
]
