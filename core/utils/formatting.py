"""Formatting utilities."""

from datetime import datetime


def format_datetime(dt: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(format_string)


def format_date(dt: datetime, format_string: str = "%Y-%m-%d") -> str:
    return dt.strftime(format_string)


def format_time(dt: datetime, format_string: str = "%H:%M:%S") -> str:
    return dt.strftime(format_string)
