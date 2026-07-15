"""Base management command with Rich console output."""

import sys
from typing import Any

from django.core.management.base import BaseCommand as DjangoBaseCommand
from rich.console import Console


class BaseCommand(DjangoBaseCommand):
    """Base command with Rich-powered output helpers.

    All project management commands inherit from this class to get
    consistent styled output via Rich. Use the helper methods instead
    of self.stdout.write or print().
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.console = Console()

    def success(self, msg: str) -> None:
        """Print a success message (green)."""
        self.console.print(msg, style="green")

    def error(self, msg: str) -> None:
        """Print an error message (red)."""
        self.console.print(msg, style="bold red")

    def warning(self, msg: str) -> None:
        """Print a warning message (yellow)."""
        self.console.print(msg, style="yellow")

    def summary_success(self, msg: str) -> None:
        """Print a final success summary and exit 0."""
        self.console.print(f"\n[bold green]OK:[/bold green] {msg}")

    def summary_failure(self, msg: str) -> None:
        """Print a final failure summary and exit 1."""
        self.console.print(f"\n[bold red]FAILED:[/bold red] {msg}")
        sys.exit(1)
