import jwt
import pytest
from django.conf import settings
from rest_framework import serializers

from apps.iam_mfa.services import _CHALLENGE_TYPE, issue_challenge_token, verify_challenge_token


class TestIssueChallengeToken:
    def test_returns_string(self) -> None:
        token = issue_challenge_token("user-123", "tenant-456")
        assert isinstance(token, str)

    def test_payload_contains_expected_claims(self) -> None:
        token = issue_challenge_token("user-123", "tenant-456")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["user_id"] == "user-123"
        assert payload["tenant_id"] == "tenant-456"
        assert payload["type"] == _CHALLENGE_TYPE

    def test_token_expires_in_5_minutes(self) -> None:
        token = issue_challenge_token("user-123", "tenant-456")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["exp"] - payload["iat"] == 300


class TestVerifyChallengeToken:
    def test_returns_user_and_tenant_ids(self) -> None:
        token = issue_challenge_token("user-123", "tenant-456")
        claims = verify_challenge_token(token)
        assert claims["user_id"] == "user-123"
        assert claims["tenant_id"] == "tenant-456"

    def test_raises_on_expired_token(self) -> None:
        from datetime import UTC, datetime, timedelta
        now = datetime.now(tz=UTC)
        expired_payload = {
            "user_id": "user-123",
            "tenant_id": "tenant-456",
            "type": _CHALLENGE_TYPE,
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=5),
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
        with pytest.raises(serializers.ValidationError) as exc_info:
            verify_challenge_token(expired_token)
        assert exc_info.value.detail["challenge_token"][0].code == "mfa_challenge_expired"

    def test_raises_on_invalid_signature(self) -> None:
        token = issue_challenge_token("user-123", "tenant-456")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(serializers.ValidationError) as exc_info:
            verify_challenge_token(tampered)
        assert exc_info.value.detail["challenge_token"][0].code == "mfa_challenge_invalid"

    def test_raises_on_wrong_type_claim(self) -> None:
        payload = jwt.decode(issue_challenge_token("u", "t"), settings.SECRET_KEY, algorithms=["HS256"])
        payload["type"] = "access"
        wrong_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        with pytest.raises(serializers.ValidationError) as exc_info:
            verify_challenge_token(wrong_token)
        assert exc_info.value.detail["challenge_token"][0].code == "mfa_challenge_invalid"
