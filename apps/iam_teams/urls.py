from rest_framework.routers import DefaultRouter

from . import views

app_name = "iam_teams"

router = DefaultRouter()

router.register("memberships", views.TeamMembershipViewSet, basename="team-membership")
router.register("", views.TeamViewSet, basename="team")

urlpatterns = router.urls
