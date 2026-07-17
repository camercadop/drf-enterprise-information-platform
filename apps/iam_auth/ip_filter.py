"""IP allowlist/blocklist enforcement for tenant login access control.

Evaluates whether a client IP is permitted to authenticate based on
per-tenant CIDR-based allowlist and blocklist settings.

Blocklist takes precedence over allowlist when both are configured.
An empty allowlist means all IPs are allowed (no restriction).
An empty blocklist means no IPs are explicitly denied.
"""

import ipaddress


def is_ip_blocked(ip: str, allowlist: list[str], blocklist: list[str]) -> bool:
    """Determine whether the given IP should be denied login access.

    Evaluation order:
    1. If the IP matches any CIDR in the blocklist, deny (blocklist wins).
    2. If the allowlist is non-empty and the IP matches no entry, deny.
    3. Otherwise, allow.

    Invalid CIDR entries are silently skipped.

    Args:
        ip: The client IP address string (IPv4 or IPv6).
        allowlist: List of CIDR strings that are explicitly permitted.
        blocklist: List of CIDR strings that are explicitly denied.

    Returns:
        True if the IP should be blocked, False if it should be allowed.
    """
    try:
        client = ipaddress.ip_address(ip)
    except ValueError:
        return False

    def matches_any(cidr_list: list[str]) -> bool:
        """Check if client IP falls within any network in the list."""
        for cidr in cidr_list:
            try:
                if client in ipaddress.ip_network(cidr, strict=False):
                    return True
            except ValueError:
                continue
        return False

    if blocklist and matches_any(blocklist):
        return True

    if allowlist and not matches_any(allowlist):
        return True

    return False
