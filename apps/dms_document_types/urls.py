from rest_framework.routers import DefaultRouter

from .views import DocumentTypeViewSet

app_name = "dms_document_types"

router = DefaultRouter()
router.register("", DocumentTypeViewSet, basename="document_type")

urlpatterns = router.urls
