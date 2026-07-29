"""Tests for core.base.commands.BaseCommand."""

import sys
from io import StringIO

import pytest


class TestBaseCommand:
    def test_success_prints_message(self) -> None:
        from core.base.commands import BaseCommand

        output = StringIO()
        cmd = BaseCommand()
        cmd.console = cmd.console.__class__(file=output)
        cmd.success("all good")
        assert "all good" in output.getvalue()

    def test_error_prints_message(self) -> None:
        from core.base.commands import BaseCommand

        output = StringIO()
        cmd = BaseCommand()
        cmd.console = cmd.console.__class__(file=output)
        cmd.error("something broke")
        assert "something broke" in output.getvalue()

    def test_warning_prints_message(self) -> None:
        from core.base.commands import BaseCommand

        output = StringIO()
        cmd = BaseCommand()
        cmd.console = cmd.console.__class__(file=output)
        cmd.warning("watch out")
        assert "watch out" in output.getvalue()

    def test_summary_success_prints_message(self) -> None:
        from core.base.commands import BaseCommand

        output = StringIO()
        cmd = BaseCommand()
        cmd.console = cmd.console.__class__(file=output)
        cmd.summary_success("done")
        assert "done" in output.getvalue()

    def test_summary_failure_exits_with_1(self) -> None:
        from core.base.commands import BaseCommand

        cmd = BaseCommand()
        with pytest.raises(SystemExit) as exc_info:
            cmd.summary_failure("failed")
        assert exc_info.value.code == 1
