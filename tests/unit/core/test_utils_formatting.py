from datetime import datetime

from core.utils.formatting import format_date, format_datetime, format_time


class TestFormatDatetime:
    def test_default_format(self) -> None:
        dt = datetime(2024, 3, 15, 10, 30, 45)
        assert format_datetime(dt) == "2024-03-15 10:30:45"

    def test_custom_format(self) -> None:
        dt = datetime(2024, 3, 15, 10, 30, 45)
        assert format_datetime(dt, "%d/%m/%Y") == "15/03/2024"


class TestFormatDate:
    def test_default_format(self) -> None:
        dt = datetime(2024, 3, 15, 10, 30, 45)
        assert format_date(dt) == "2024-03-15"

    def test_custom_format(self) -> None:
        dt = datetime(2024, 3, 15)
        assert format_date(dt, "%m-%d-%Y") == "03-15-2024"


class TestFormatTime:
    def test_default_format(self) -> None:
        dt = datetime(2024, 3, 15, 10, 30, 45)
        assert format_time(dt) == "10:30:45"

    def test_custom_format(self) -> None:
        dt = datetime(2024, 3, 15, 10, 30, 45)
        assert format_time(dt, "%H:%M") == "10:30"
