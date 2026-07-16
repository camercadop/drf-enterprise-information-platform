from rest_framework.routers import DefaultRouter

from . import views

app_name = "tenant_settings"

router = DefaultRouter()
router.register("", views.TenantSettingViewSet, basename="tenant-setting")

urlpatterns = router.urls
