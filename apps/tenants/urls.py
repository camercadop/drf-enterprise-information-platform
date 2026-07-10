from rest_framework.routers import DefaultRouter

from . import views

app_name = "tenants"

router = DefaultRouter()
router.register("", views.TenantViewSet, basename="tenant")
router.register("teams", views.TeamViewSet, basename="team")
router.register("memberships", views.MembershipViewSet, basename="membership")

urlpatterns = router.urls
