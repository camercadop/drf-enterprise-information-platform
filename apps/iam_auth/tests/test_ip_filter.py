from apps.iam_auth.ip_filter import is_ip_blocked


class TestIsIpBlockedBlocklist:
    """Tests for blocklist evaluation."""

    def test_ip_in_blocklist_is_blocked(self) -> None:
        assert is_ip_blocked("192.168.1.1", [], ["192.168.1.0/24"]) is True

    def test_ip_not_in_blocklist_is_allowed(self) -> None:
        assert is_ip_blocked("10.0.0.1", [], ["192.168.1.0/24"]) is False

    def test_blocklist_wins_over_allowlist(self) -> None:
        assert is_ip_blocked("192.168.1.1", ["192.168.1.0/24"], ["192.168.1.0/24"]) is True

    def test_exact_ip_in_blocklist(self) -> None:
        assert is_ip_blocked("10.0.0.5", [], ["10.0.0.5/32"]) is True

    def test_ip_outside_blocklist_cidr_is_allowed(self) -> None:
        assert is_ip_blocked("10.0.0.5", [], ["10.0.0.0/30"]) is False


class TestIsIpBlockedAllowlist:
    """Tests for allowlist evaluation."""

    def test_ip_in_allowlist_is_allowed(self) -> None:
        assert is_ip_blocked("192.168.1.1", ["192.168.1.0/24"], []) is False

    def test_ip_not_in_allowlist_is_blocked(self) -> None:
        assert is_ip_blocked("10.0.0.1", ["192.168.1.0/24"], []) is True

    def test_empty_allowlist_allows_all(self) -> None:
        assert is_ip_blocked("10.0.0.1", [], []) is False

    def test_ip_matches_one_of_multiple_allowlist_entries(self) -> None:
        assert is_ip_blocked("172.16.0.1", ["10.0.0.0/8", "172.16.0.0/12"], []) is False

    def test_ip_matches_none_of_multiple_allowlist_entries(self) -> None:
        assert is_ip_blocked("8.8.8.8", ["10.0.0.0/8", "172.16.0.0/12"], []) is True


class TestIsIpBlockedEdgeCases:
    """Tests for edge cases and invalid inputs."""

    def test_invalid_ip_is_allowed(self) -> None:
        assert is_ip_blocked("not-an-ip", ["10.0.0.0/8"], ["192.168.0.0/16"]) is False

    def test_empty_ip_is_allowed(self) -> None:
        assert is_ip_blocked("", ["10.0.0.0/8"], []) is False

    def test_invalid_cidr_in_blocklist_is_skipped(self) -> None:
        assert is_ip_blocked("10.0.0.1", [], ["not-a-cidr", "10.0.0.0/8"]) is True

    def test_invalid_cidr_in_allowlist_is_skipped(self) -> None:
        assert is_ip_blocked("10.0.0.1", ["not-a-cidr"], []) is True

    def test_ipv6_in_blocklist(self) -> None:
        assert is_ip_blocked("::1", [], ["::1/128"]) is True

    def test_ipv6_not_in_blocklist(self) -> None:
        assert is_ip_blocked("::2", [], ["::1/128"]) is False
