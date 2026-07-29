import base64
import hashlib
from unittest.mock import MagicMock

from apps.iam_oauth.services import _verify_pkce


class TestVerifyPkce:
    def test_s256_valid(self) -> None:
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        auth_code = MagicMock()
        auth_code.code_challenge = challenge
        auth_code.code_challenge_method = "S256"
        _verify_pkce(verifier, auth_code)  # must not raise

    def test_s256_invalid(self) -> None:
        import pytest
        from rest_framework.exceptions import ValidationError

        auth_code = MagicMock()
        auth_code.code_challenge = "wrong_challenge"
        auth_code.code_challenge_method = "S256"
        with pytest.raises(ValidationError):
            _verify_pkce("any_verifier", auth_code)

    def test_plain_valid(self) -> None:
        auth_code = MagicMock()
        auth_code.code_challenge = "my_verifier"
        auth_code.code_challenge_method = "plain"
        _verify_pkce("my_verifier", auth_code)  # must not raise

    def test_plain_invalid(self) -> None:
        import pytest
        from rest_framework.exceptions import ValidationError

        auth_code = MagicMock()
        auth_code.code_challenge = "expected"
        auth_code.code_challenge_method = "plain"
        with pytest.raises(ValidationError):
            _verify_pkce("wrong", auth_code)
