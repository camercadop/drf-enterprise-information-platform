"""URL configuration for DMS Metadata API."""

from rest_framework.routers import DefaultRouter

from .views import MetadataDefinitionViewSet

app_name = "dms_metadata"

router = DefaultRouter()
router.register("", MetadataDefinitionViewSet, basename="metadata_definition")

urlpatterns = router.urls
