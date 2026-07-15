from rest_framework.routers import DefaultRouter

from . import views

app_name = "iam_roles"

router = DefaultRouter()
router.register("", views.TenantRoleViewSet, basename="role")

urlpatterns = router.urls
