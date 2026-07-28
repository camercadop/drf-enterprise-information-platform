"""Formatting utilities."""

from datetime import datetime


def format_datetime(dt: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(format_string)


def format_date(dt: datetime, format_string: str = "%Y-%m-%d") -> str:
    return dt.strftime(format_string)


def format_time(dt: datetime, format_string: str = "%H:%M:%S") -> str:
    return dt.strftime(format_string)


def format_human_size(size_bytes: int) -> str:
    """Return a human-readable string representation of a byte size.

    Args:
        size_bytes: Size in bytes. Must be a non-negative integer.

    Returns:
        A string like "1.5 MB" or "300 KB", using the largest applicable unit.
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} PB"
