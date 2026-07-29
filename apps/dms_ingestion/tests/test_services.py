"""Tests for dms_ingestion.services.run_pipeline."""

from unittest.mock import patch

import pytest

from apps.dms_ingestion.models import UploadSession
from apps.dms_ingestion.services import run_pipeline
from tests.factories.dms_ingestion import UploadSessionFactory


@pytest.mark.django_db
class TestRunPipelineIdempotency:
    def test_skips_already_completed_session(self) -> None:
        session = UploadSessionFactory(state=UploadSession.State.DOCUMENT_CREATED)

        with patch("apps.dms_ingestion.services.publish") as mock_publish:
            run_pipeline(str(session.id))

        mock_publish.assert_not_called()

    def test_does_not_change_state_of_completed_session(self) -> None:
        session = UploadSessionFactory(state=UploadSession.State.DOCUMENT_CREATED)

        run_pipeline(str(session.id))

        session.refresh_from_db()
        assert session.state == UploadSession.State.DOCUMENT_CREATED


@pytest.mark.django_db
class TestRunPipelineAtomicity:
    def test_state_not_updated_when_publish_fails(self) -> None:
        session = UploadSessionFactory(
            state=UploadSession.State.NEW,
            storage_key="session/file.pdf",
            mime_type="application/pdf",
            filename="file.pdf",
            size=1024,
        )

        with (
            patch("apps.dms_ingestion.services.get_storage_backend") as mock_storage,
            patch("apps.dms_ingestion.services.build_pipeline", return_value=[]),
            patch("apps.dms_ingestion.services.publish", side_effect=RuntimeError("redis down")),
        ):
            mock_storage.return_value.open.return_value.__enter__ = lambda s: s
            mock_storage.return_value.open.return_value.__exit__ = lambda *a: False

            with pytest.raises(RuntimeError, match="redis down"):
                run_pipeline(str(session.id))

        session.refresh_from_db()
        assert session.state != UploadSession.State.DOCUMENT_CREATED
