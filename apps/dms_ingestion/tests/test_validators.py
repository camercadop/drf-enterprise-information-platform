"""Unit tests for dms_ingestion validators."""

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings


class TestValidateFileSize:
    def test_passes_when_size_within_limit(self) -> None:
        from apps.dms_ingestion.validators import validate_file_size

        with override_settings(APP_DMS_INGESTION={"MAX_FILE_SIZE_BYTES": 1024}):
            validate_file_size(512)

    def test_passes_when_size_equals_limit(self) -> None:
        from apps.dms_ingestion.validators import validate_file_size

        with override_settings(APP_DMS_INGESTION={"MAX_FILE_SIZE_BYTES": 1024}):
            validate_file_size(1024)

    def test_raises_when_size_exceeds_limit(self) -> None:
        from apps.dms_ingestion.validators import validate_file_size

        with override_settings(APP_DMS_INGESTION={"MAX_FILE_SIZE_BYTES": 1024}):
            with pytest.raises(ValidationError):
                validate_file_size(2048)


class TestValidateMimeType:
    def test_passes_when_allowed_list_is_empty(self) -> None:
        from apps.dms_ingestion.validators import validate_mime_type

        with override_settings(APP_DMS_INGESTION={"ALLOWED_MIME_TYPES": []}):
            validate_mime_type("application/octet-stream")

    def test_passes_when_mime_type_is_allowed(self) -> None:
        from apps.dms_ingestion.validators import validate_mime_type

        with override_settings(APP_DMS_INGESTION={"ALLOWED_MIME_TYPES": ["application/pdf"]}):
            validate_mime_type("application/pdf")

    def test_raises_when_mime_type_not_allowed(self) -> None:
        from apps.dms_ingestion.validators import validate_mime_type

        with override_settings(APP_DMS_INGESTION={"ALLOWED_MIME_TYPES": ["application/pdf"]}):
            with pytest.raises(ValidationError):
                validate_mime_type("image/png")


class TestValidateExtension:
    def test_passes_when_allowed_list_is_empty(self) -> None:
        from apps.dms_ingestion.validators import validate_extension

        with override_settings(APP_DMS_INGESTION={"ALLOWED_EXTENSIONS": []}):
            validate_extension("file.exe")

    def test_passes_when_extension_is_allowed(self) -> None:
        from apps.dms_ingestion.validators import validate_extension

        with override_settings(APP_DMS_INGESTION={"ALLOWED_EXTENSIONS": [".pdf"]}):
            validate_extension("document.pdf")

    def test_passes_case_insensitive(self) -> None:
        from apps.dms_ingestion.validators import validate_extension

        with override_settings(APP_DMS_INGESTION={"ALLOWED_EXTENSIONS": [".pdf"]}):
            validate_extension("document.PDF")

    def test_raises_when_extension_not_allowed(self) -> None:
        from apps.dms_ingestion.validators import validate_extension

        with override_settings(APP_DMS_INGESTION={"ALLOWED_EXTENSIONS": [".pdf"]}):
            with pytest.raises(ValidationError):
                validate_extension("file.exe")
