"""
Metadata type definitions for DMS Metadata.
"""

from django.db import models


class MetadataType(models.TextChoices):
    """Enumeration of supported metadata data types."""

    STRING = "STRING", "String"
    TEXT = "TEXT", "Text"
    INTEGER = "INTEGER", "Integer"
    DECIMAL = "DECIMAL", "Decimal"
    BOOLEAN = "BOOLEAN", "Boolean"
    DATE = "DATE", "Date"
    DATETIME = "DATETIME", "DateTime"
    TIME = "TIME", "Time"
    UUID = "UUID", "UUID"
    EMAIL = "EMAIL", "Email"
    URL = "URL", "URL"
    JSON = "JSON", "JSON"
    ENUM = "ENUM", "Enum"
