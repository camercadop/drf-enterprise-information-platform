"""Unit tests for dms_ingestion processors."""

import hashlib
import io
from unittest.mock import MagicMock

from django.test import override_settings


class TestChecksumProcessor:
    def test_sets_checksum_on_session(self) -> None:
        from apps.dms_ingestion.processors import ChecksumProcessor

        content = b"hello world"
        expected = hashlib.sha256(content).hexdigest()
        session = MagicMock()
        processor = ChecksumProcessor()

        processor.process(session, io.BytesIO(content))

        assert session.checksum == expected

    def test_rewinds_file_after_processing(self) -> None:
        from apps.dms_ingestion.processors import ChecksumProcessor

        file = io.BytesIO(b"data")
        session = MagicMock()
        ChecksumProcessor().process(session, file)

        assert file.tell() == 0


class TestMetadataProcessor:
    def test_sets_extension_from_filename(self) -> None:
        from apps.dms_ingestion.processors import MetadataProcessor

        session = MagicMock()
        session.filename = "report.PDF"
        MetadataProcessor().process(session, io.BytesIO())

        assert session.extension == ".pdf"

    def test_sets_none_when_no_extension(self) -> None:
        from apps.dms_ingestion.processors import MetadataProcessor

        session = MagicMock()
        session.filename = "Makefile"
        MetadataProcessor().process(session, io.BytesIO())

        assert session.extension is None


class TestBuildPipeline:
    def test_returns_configured_processors_in_order(self) -> None:
        from apps.dms_ingestion.processors import (
            ChecksumProcessor,
            MetadataProcessor,
            build_pipeline,
        )

        settings_override = {
            "PIPELINE_PROCESSORS": [
                "apps.dms_ingestion.processors.ChecksumProcessor",
                "apps.dms_ingestion.processors.MetadataProcessor",
            ]
        }
        with override_settings(APP_DMS_INGESTION=settings_override):
            pipeline = build_pipeline()

        assert len(pipeline) == 2
        assert isinstance(pipeline[0], ChecksumProcessor)
        assert isinstance(pipeline[1], MetadataProcessor)

    def test_returns_empty_list_when_no_processors_configured(self) -> None:
        from apps.dms_ingestion.processors import build_pipeline

        with override_settings(APP_DMS_INGESTION={"PIPELINE_PROCESSORS": []}):
            pipeline = build_pipeline()

        assert pipeline == []
