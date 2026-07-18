"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.iam_auth.urls")),
    path("api/sys/", include("apps.sys_user_event.urls")),
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/tenant-settings/", include("apps.tenant_settings.urls")),
    path("api/teams/", include("apps.iam_teams.urls")),
    path("api/roles/", include("apps.iam_roles.urls")),
    path("api/users/", include("apps.iam_users.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="schema-swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="schema-redoc",
    ),
    path("health/", include("apps.sys_health.urls")),
]
