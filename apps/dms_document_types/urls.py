from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DocumentTypeViewSet

app_name = "dms_document_types"

router = DefaultRouter()
router.register("", DocumentTypeViewSet, basename="document_type")

urlpatterns = router.urls + [
    path("<uuid:document_type_id>/metadata-definitions/", include("apps.dms_metadata.urls")),
]
