import uuid
import pytest
from app.services.crypto import crypto_service


def test_aes_256_gcm_encryption_and_decryption():
    raw_token = "nexus_sample_refresh_token_string_12345"
    family_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    encrypted = crypto_service.encrypt_token(raw_token, family_id, user_id)
    assert encrypted != raw_token
    assert len(encrypted) > 20

    # Decrypt with matching AAD (family_id, user_id)
    decrypted = crypto_service.decrypt_token(encrypted, family_id, user_id)
    assert decrypted == raw_token


def test_aes_256_gcm_aad_mismatch_fails():
    raw_token = "nexus_sample_refresh_token_string_12345"
    family_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())

    encrypted = crypto_service.encrypt_token(raw_token, family_id, user_id)

    # Decrypt with wrong user_id (AAD mismatch) must return None
    decrypted = crypto_service.decrypt_token(encrypted, family_id, other_user_id)
    assert decrypted is None


def test_corrupted_ciphertext_fails():
    family_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    assert crypto_service.decrypt_token("invalid_base64_payload!", family_id, user_id) is None

