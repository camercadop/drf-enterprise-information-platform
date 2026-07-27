"""URL configuration for Document Versions API."""

from rest_framework.routers import DefaultRouter

from .views import DocumentVersionViewSet

app_name = "dms_document_versions"

router = DefaultRouter()
router.register("", DocumentVersionViewSet, basename="document_version")

urlpatterns = router.urls
