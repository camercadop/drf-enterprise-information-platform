"""Unit tests for dms_ingestion storage."""

import io
from unittest.mock import MagicMock


class TestGenerateStorageName:
    def test_returns_session_scoped_path(self) -> None:
        from apps.dms_ingestion.storage import generate_storage_name

        file = MagicMock()
        file.name = "invoice.pdf"
        result = generate_storage_name("abc-123", file)

        assert result.startswith("abc-123/")
        assert result.endswith("_invoice.pdf")

    def test_timestamp_format(self) -> None:
        from apps.dms_ingestion.storage import generate_storage_name

        file = MagicMock()
        file.name = "file.txt"
        result = generate_storage_name("session-1", file)

        # Extract timestamp portion: session-1/<timestamp>_file.txt
        timestamp = result.split("/")[1].split("_file.txt")[0]
        assert len(timestamp) == 15  # YYYYmmdd_HHMMSS
        assert timestamp[8] == "_"

    def test_falls_back_to_session_id_when_no_name(self) -> None:
        from apps.dms_ingestion.storage import generate_storage_name

        file = MagicMock(spec=[])  # no name attribute
        result = generate_storage_name("session-1", file)

        assert result.startswith("session-1/")
        assert "session-1" in result


class TestInMemoryStorageBackend:
    def test_save_and_open_roundtrip(self) -> None:
        from apps.dms_ingestion.storage import InMemoryStorageBackend

        backend = InMemoryStorageBackend()
        content = b"test content"
        file = MagicMock()
        file.name = "test.txt"
        file.read.return_value = content

        key = backend.save("session-1", file)
        result = backend.open(key).read()

        assert result == content

    def test_delete_removes_file(self) -> None:
        from apps.dms_ingestion.storage import InMemoryStorageBackend

        backend = InMemoryStorageBackend()
        file = MagicMock()
        file.name = "test.txt"
        file.read.return_value = b"data"

        key = backend.save("session-1", file)
        backend.delete(key)

        assert key not in backend._store

    def test_delete_nonexistent_key_does_not_raise(self) -> None:
        from apps.dms_ingestion.storage import InMemoryStorageBackend

        backend = InMemoryStorageBackend()
        backend.delete("nonexistent-key")

    def test_open_returns_fresh_bytesio(self) -> None:
        from apps.dms_ingestion.storage import InMemoryStorageBackend

        backend = InMemoryStorageBackend()
        file = MagicMock()
        file.name = "f.bin"
        file.read.return_value = b"abc"

        key = backend.save("s", file)

        assert isinstance(backend.open(key), io.BytesIO)
