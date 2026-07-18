from rest_framework.routers import DefaultRouter

from . import views

app_name = "sys_user_event"

router = DefaultRouter()
router.register("user-events", views.UserEventViewSet, basename="user-event")
router.register("auth-attempts", views.AuthAttemptLogViewSet, basename="auth-attempt")

urlpatterns = router.urls
