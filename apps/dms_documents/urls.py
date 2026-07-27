"""URL configuration for DMS Documents API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet

app_name = "dms_documents"

router = DefaultRouter()
router.register("", DocumentViewSet, basename="document")

urlpatterns = router.urls + [
    path("<uuid:document_id>/versions/", include("apps.dms_document_versions.urls")),
]
