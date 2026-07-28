"""Celery tasks for DMS Ingestion."""

import logging

from celery import shared_task

from apps.dms_ingestion import services

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
)
def run_pipeline_task(session_id: str) -> None:
    """Execute the ingestion pipeline for an uploaded session.

    Thin wrapper over services.run_pipeline. Retries up to 3 times with
    exponential backoff on any exception. After exhausting retries, the
    exception propagates and the task moves to the Celery failure state.

    Args:
        session_id: UUID string of the UploadSession to process.
    """
    logger.info("Starting pipeline task for session %s", session_id)
    services.run_pipeline(session_id)
