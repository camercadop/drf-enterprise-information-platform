"""Processors for the DMS Ingestion pipeline.

Each processor implements process(session, file) and mutates the session
in place. Processors are stateless and run sequentially by services.run_pipeline.
"""

import hashlib
import logging
import os
from typing import IO, Protocol

from django.conf import settings

from apps.dms_ingestion.models import UploadSession
from core.module_resolver import resolve_instance

logger = logging.getLogger(__name__)


class Processor(Protocol):
    """Contract that all pipeline processors must satisfy.

    Implementations must be stateless. Each processor mutates the session
    in place and must not persist changes to the DB — persistence is the
    responsibility of services.run_pipeline.
    """

    def process(self, session: UploadSession, file: IO[bytes]) -> None:
        """Process the uploaded file and update the session in place.

        Args:
            session: The upload session to update.
            file: A file-like object opened in binary mode.
        """
        ...


def build_pipeline() -> list[Processor]:
    """Instantiate and return the configured pipeline processors in order.

    Resolves each dotted path in APP_DMS_INGESTION["PIPELINE_PROCESSORS"] via
    core.module_resolver.resolve_instance. Raises ImportError or AttributeError if a path
    is invalid.

    Returns:
        A list of Processor instances ready to be called sequentially.
    """
    return [
        resolve_instance(path)
        for path in settings.APP_DMS_INGESTION["PIPELINE_PROCESSORS"]
    ]


class ChecksumProcessor:
    """Computes the SHA-256 checksum of the uploaded file and stores it on the session.

    Reads the file in chunks to avoid loading large files into memory at once.
    Rewinds the file to the start before reading so downstream processors
    receive a fresh file pointer.
    """

    CHUNK_SIZE = 8192

    def process(self, session: UploadSession, file: IO[bytes]) -> None:
        """Compute SHA-256 digest and set session.checksum.

        Args:
            session: The upload session to update.
            file: A file-like object opened in binary mode.
        """
        file.seek(0)
        digest = hashlib.sha256()
        while chunk := file.read(self.CHUNK_SIZE):
            digest.update(chunk)
        session.checksum = digest.hexdigest()
        file.seek(0)
        logger.info(
            "Checksum computed for session %s: %s", session.id, session.checksum
        )


class MetadataProcessor:
    """Derives file metadata from the session and stores it on the session.

    Currently extracts the file extension from session.filename.
    """

    def process(self, session: UploadSession, file: IO[bytes]) -> None:
        """Derive and set session.extension from session.filename.

        Args:
            session: The upload session to update.
            file: A file-like object opened in binary mode (not read by this processor).
        """
        _, ext = os.path.splitext(session.filename)
        session.extension = ext.lower() or None
        logger.info(
            "Extension derived for session %s: %s", session.id, session.extension
        )
