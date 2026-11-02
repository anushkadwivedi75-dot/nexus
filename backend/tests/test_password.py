import pytest
from app.services.password import password_service


def test_password_hashing_and_verification():
    raw_password = "SecurePassword123!#"
    hashed = password_service.hash_password(raw_password)

    # Must be valid Argon2id format
    assert hashed.startswith("$argon2id$")
    assert "m=65536,t=3,p=4" in hashed

    # Valid password verification succeeds
    assert password_service.verify_password(raw_password, hashed) is True

    # Invalid password verification fails
    assert password_service.verify_password("WrongPassword123!#", hashed) is False
    assert password_service.verify_password("", hashed) is False
    assert password_service.verify_password(raw_password, "") is False


def test_password_short_length_rejected():
    with pytest.raises(ValueError):
        password_service.hash_password("short1")


def test_timing_dummy_verification():
    # Calling verify_dummy does not raise any exception
    password_service.verify_dummy()
