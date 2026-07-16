from rest_framework.routers import DefaultRouter

from . import views

app_name = "tenants"

router = DefaultRouter()
router.register("memberships", views.MembershipViewSet, basename="membership")
router.register("", views.TenantViewSet, basename="tenant")

urlpatterns = router.urls
