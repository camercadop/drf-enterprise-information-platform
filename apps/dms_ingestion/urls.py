"""URL configuration for DMS Ingestion API."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import UploadSessionViewSet, UploadView

app_name = "dms_ingestion"

router = DefaultRouter()
router.register("upload-sessions", UploadSessionViewSet, basename="upload-session")

urlpatterns = router.urls + [
    path(
        "upload-sessions/<uuid:pk>/upload/",
        UploadView.as_view(),
        name="upload-session-upload",
    ),
]
