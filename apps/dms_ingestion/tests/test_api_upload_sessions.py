"""API tests for dms_ingestion endpoints."""

import pytest

from tests.base import BaseActionAPITest, BaseCreateAPITest, BaseListAPITest, BaseRetrieveAPITest
from tests.factories.dms_ingestion import UploadSessionFactory


class TestUploadSessionViewSet(BaseCreateAPITest, BaseListAPITest, BaseRetrieveAPITest):
    """Tests for POST/GET /api/dms/ingestion/upload-sessions/."""

    url = "/api/dms/ingestion/upload-sessions/"

    def create_instance(self):  # type: ignore[override]
        return UploadSessionFactory(tenant=self.membership.tenant)

    def valid_payloads(self):  # type: ignore[override]
        return [
            {
                "title": "My Document",
                "filename": "report.pdf",
                "mime_type": "application/pdf",
                "size": 2048,
            },
        ]

    def invalid_payloads(self):  # type: ignore[override]
        return [
            ({}, None),
            ({"title": "", "filename": "f.pdf", "mime_type": "application/pdf", "size": 1}, None),
        ]


class TestUploadView(BaseActionAPITest):
    """Smoke test for PUT /api/dms/ingestion/upload-sessions/{id}/upload/."""

    url = ""
    http_method = "put"

    @pytest.fixture(autouse=True)
    def _setup_upload(self, auth_client, user, membership) -> None:  # type: ignore[override]
        self.client = auth_client
        self.user = user
        self.membership = membership
        session = UploadSessionFactory(tenant=membership.tenant)
        self.url = f"/api/dms/ingestion/upload-sessions/{session.pk}/upload/"

    def test_smoke(self) -> None:
        response = self.client.put(self.url)
        assert response.status_code // 100 in (2, 4)
