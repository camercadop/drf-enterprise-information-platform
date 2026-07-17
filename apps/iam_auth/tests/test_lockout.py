import pytest
from django.core.cache import cache

from apps.iam_auth.lockout import clear_lockout, is_locked, record_failed_attempt


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear cache before each test to avoid state leakage."""
    cache.clear()


class TestIsLocked:
    """Tests for is_locked."""

    def test_returns_false_when_no_lockout_key(self) -> None:
        assert is_locked("user@example.com") is False

    def test_returns_true_when_lockout_key_exists(self) -> None:
        cache.set("auth:lockout:locked:user@example.com", 1)
        assert is_locked("user@example.com") is True


class TestRecordFailedAttempt:
    """Tests for record_failed_attempt."""

    def test_increments_attempt_counter(self) -> None:
        record_failed_attempt("user@example.com")
        assert cache.get("auth:lockout:attempts:user@example.com") == 1

    def test_increments_on_subsequent_calls(self) -> None:
        record_failed_attempt("user@example.com")
        record_failed_attempt("user@example.com")
        assert cache.get("auth:lockout:attempts:user@example.com") == 2

    def test_sets_lockout_flag_when_threshold_reached(self, settings: object) -> None:
        settings.AUTH_LOCKOUT = {"MAX_ATTEMPTS": 3, "LOCKOUT_DURATION": 900}  # type: ignore[attr-defined]
        record_failed_attempt("user@example.com")
        record_failed_attempt("user@example.com")
        assert not is_locked("user@example.com")
        record_failed_attempt("user@example.com")
        assert is_locked("user@example.com")

    def test_does_nothing_when_max_attempts_is_zero(self, settings: object) -> None:
        settings.AUTH_LOCKOUT = {"MAX_ATTEMPTS": 0, "LOCKOUT_DURATION": 900}  # type: ignore[attr-defined]
        record_failed_attempt("user@example.com")
        assert cache.get("auth:lockout:attempts:user@example.com") is None
        assert not is_locked("user@example.com")

    def test_no_ttl_when_lockout_duration_is_zero(self, settings: object) -> None:
        settings.AUTH_LOCKOUT = {"MAX_ATTEMPTS": 1, "LOCKOUT_DURATION": 0}  # type: ignore[attr-defined]
        record_failed_attempt("user@example.com")
        assert is_locked("user@example.com")

    def test_isolated_per_email(self) -> None:
        record_failed_attempt("a@example.com")
        assert cache.get("auth:lockout:attempts:b@example.com") is None


class TestClearLockout:
    """Tests for clear_lockout."""

    def test_clears_attempts_and_locked_keys(self) -> None:
        cache.set("auth:lockout:attempts:user@example.com", 3)
        cache.set("auth:lockout:locked:user@example.com", 1)
        clear_lockout("user@example.com")
        assert cache.get("auth:lockout:attempts:user@example.com") is None
        assert not is_locked("user@example.com")

    def test_no_error_when_keys_do_not_exist(self) -> None:
        clear_lockout("user@example.com")  # should not raise
