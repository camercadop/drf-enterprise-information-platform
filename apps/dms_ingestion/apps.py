"""App configuration for DMS Ingestion."""

from django.apps import AppConfig


class DmsIngestionConfig(AppConfig):
    """Configuration for the dms_ingestion app."""

    name = "apps.dms_ingestion"
    label = "dms_ingestion"
    verbose_name = "DMS Ingestion"
