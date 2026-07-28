"""Storage abstraction for DMS Ingestion.

Defines the StorageProvider Protocol, concrete backends, and the
get_storage_backend() factory. Swap the backend via
APP_DMS_INGESTION["STORAGE_BACKEND"] without changing any call sites.
Swap the filename generator via APP_DMS_INGESTION["STORAGE_NAME_GENERATOR"].
"""

import io
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import IO, Protocol

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from core.module_resolver import resolve, resolve_instance

logger = logging.getLogger(__name__)


def generate_storage_name(session_id: str, file: IO[bytes]) -> str:
    """Generate a timestamped storage path for an uploaded file.

    Produces a path of the form ``<session_id>/<YYYYmmdd_HHMMSS>_<filename>``.
    Used as the default STORAGE_NAME_GENERATOR. Override via
    APP_DMS_INGESTION["STORAGE_NAME_GENERATOR"] to customise naming.

    Args:
        session_id: The upload session UUID as a string.
        file: A file-like object with a ``name`` attribute.

    Returns:
        A string storage path scoped to the session.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = getattr(file, "name", session_id)
    return f"{session_id}/{timestamp}_{filename}"


class StorageProvider(Protocol):
    """Contract that all storage backends must satisfy.

    Implementations must be stateless and thread-safe. Use save() to persist
    a file and delete() to remove it. The returned storage key is opaque to
    callers — pass it back to open() and delete() verbatim.
    """

    def save(self, session_id: str, file: IO[bytes]) -> str:
        """Persist a file and return its storage key.

        Args:
            session_id: The upload session UUID as a string, used to derive
                a unique storage path.
            file: A file-like object opened in binary mode.

        Returns:
            An opaque storage key that can be passed to open() or delete().
        """
        ...

    def open(self, storage_key: str) -> IO[bytes]:
        """Open a previously saved file for reading.

        Args:
            storage_key: The value returned by save().

        Returns:
            A file-like object opened in binary mode.
        """
        ...

    def delete(self, storage_key: str) -> None:
        """Remove a previously saved file.

        Args:
            storage_key: The value returned by save().
        """
        ...


class BaseStorageBackend(ABC):
    """Abstract base for all storage backends.

    Provides the public save() method, which resolves the configured name
    generator and delegates to the abstract _save() hook. Subclasses must
    implement _save(), open(), and delete().
    """

    def save(self, session_id: str, file: IO[bytes]) -> str:
        """Generate a storage name and persist the file via _save().

        Args:
            session_id: The upload session UUID as a string.
            file: A file-like object opened in binary mode.

        Returns:
            An opaque storage key that can be passed to open() or delete().
        """
        name = _resolve_name_generator()(session_id, file)
        return self._save(name, file)

    @abstractmethod
    def _save(self, name: str, file: IO[bytes]) -> str:
        """Persist the file under the given name and return the storage key.

        Args:
            name: The resolved storage path produced by the name generator.
            file: A file-like object opened in binary mode.

        Returns:
            An opaque storage key that can be passed to open() or delete().
        """

    @abstractmethod
    def open(self, storage_key: str) -> IO[bytes]:
        """Open a previously saved file for reading.

        Args:
            storage_key: The value returned by save().

        Returns:
            A file-like object opened in binary mode.
        """

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove a previously saved file.

        Args:
            storage_key: The value returned by save().
        """


class LocalStorageBackend(BaseStorageBackend):
    """Stores files on the local filesystem via Django's FileSystemStorage.

    Location is configured via APP_DMS_INGESTION["STORAGE_LOCATION"].
    Intended for local development and single-server deployments. For
    cloud storage, swap to an S3 or GCS backend via the settings key.
    """

    def __init__(self) -> None:
        """Initialise the backend using the configured storage location."""
        location: str = settings.APP_DMS_INGESTION["STORAGE_LOCATION"]
        self._storage = FileSystemStorage(location=location)

    def _save(self, name: str, file: IO[bytes]) -> str:
        """Save the file to the local filesystem and return the storage key.

        Args:
            name: The resolved storage path.
            file: A file-like object opened in binary mode.

        Returns:
            The storage key (relative path) assigned by FileSystemStorage.
        """
        storage_key: str = self._storage.save(name, file)  # type: ignore[arg-type]
        logger.info("File saved to local storage: %s", storage_key)
        return storage_key

    def open(self, storage_key: str) -> IO[bytes]:
        """Open a previously saved file for reading.

        Args:
            storage_key: The value returned by save().

        Returns:
            A file-like object opened in binary mode.
        """
        result: IO[bytes] = self._storage.open(storage_key, mode="rb")  # type: ignore[assignment]
        return result

    def delete(self, storage_key: str) -> None:
        """Delete the file at the given storage key.

        Args:
            storage_key: The value returned by save().
        """
        self._storage.delete(storage_key)
        logger.info("File deleted from local storage: %s", storage_key)


class InMemoryStorageBackend(BaseStorageBackend):
    """In-memory storage backend for use in tests.

    Stores file contents in a dict — no filesystem or cloud dependency.
    Not thread-safe and not suitable for production use.
    """

    def __init__(self) -> None:
        """Initialise an empty in-memory store."""
        self._store: dict[str, bytes] = {}

    def _save(self, name: str, file: IO[bytes]) -> str:
        """Store file contents in memory under the given name.

        Args:
            name: The resolved storage key.
            file: A file-like object opened in binary mode.

        Returns:
            The storage key (name).
        """
        self._store[name] = file.read()
        return name

    def open(self, storage_key: str) -> IO[bytes]:
        """Return a BytesIO object for the stored file content.

        Args:
            storage_key: The value returned by save().

        Returns:
            A file-like object opened in binary mode.
        """
        return io.BytesIO(self._store[storage_key])

    def delete(self, storage_key: str) -> None:
        """Remove the stored file content.

        Args:
            storage_key: The value returned by save().
        """
        self._store.pop(storage_key, None)


def _resolve_name_generator() -> Callable[[str, IO[bytes]], str]:
    """Resolve the configured storage name generator callable.

    Reads APP_DMS_INGESTION["STORAGE_NAME_GENERATOR"] and resolves it via
    core.module_resolver.resolve. Falls back to generate_storage_name if the key is absent.

    Returns:
        The resolved StorageNameGenerator callable.
    """
    dotted_path: str = settings.APP_DMS_INGESTION.get(
        "STORAGE_NAME_GENERATOR",
        "apps.dms_ingestion.storage.generate_storage_name",
    )
    return resolve(dotted_path)  # type: ignore[no-any-return]


def get_storage_backend() -> StorageProvider:
    """Instantiate and return the configured storage backend.

    Resolves APP_DMS_INGESTION["STORAGE_BACKEND"] via core.module_resolver.resolve_instance.
    Raises ImportError or AttributeError if the path is invalid.

    Returns:
        An instantiated StorageProvider implementation.
    """
    return resolve_instance(settings.APP_DMS_INGESTION["STORAGE_BACKEND"])  # type: ignore[no-any-return]
