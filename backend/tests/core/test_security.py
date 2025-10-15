from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password


settings = get_settings()


def test_hash_password_roundtrip() -> None:
    password = "SecurePass123!"
    stored = hash_password(password)

    assert stored != password
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password(password, stored) is True
    assert verify_password("WrongPass456!", stored) is False


def test_hash_password_uses_random_salt() -> None:
    password = "AnotherStrongPass456!"
    first = hash_password(password)
    second = hash_password(password)

    assert first != second
    assert verify_password(password, first) is True
    assert verify_password(password, second) is True


def test_hash_password_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_create_access_token_payload_contains_expected_claims() -> None:
    user_id = uuid.uuid4()
    token, expires_at = create_access_token(
        user_id,
        email="tokentest@example.com",
        expires_delta=timedelta(minutes=15),
        settings=settings,
    )

    assert expires_at - datetime.now(timezone.utc) <= timedelta(minutes=15, seconds=1)

    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "tokentest@example.com"
    assert payload["iss"] == settings.app_name
    assert "exp" in payload
    assert "iat" in payload
