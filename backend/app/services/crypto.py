import base64
import os
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

logger = logging.getLogger(__name__)


class GraceStashCrypto:
    def __init__(self):
        # 256-bit (32 bytes) key from hex
        key_hex = settings.TOKEN_ENCRYPTION_KEY
        try:
            self._key = bytes.fromhex(key_hex)
            if len(self._key) != 32:
                raise ValueError("TOKEN_ENCRYPTION_KEY must be exactly 32 bytes (64 hex characters)")
        except Exception as e:
            logger.warning("Invalid TOKEN_ENCRYPTION_KEY hex format, falling back to padded bytes: %s", e)
            self._key = key_hex.encode("utf-8")[:32].ljust(32, b"0")

    def encrypt_token(self, token: str, family_id: str, user_id: str) -> str:
        """
        Encrypts a raw refresh token using AES-256-GCM.
        AAD binds the ciphertext to the exact family_id:user_id.
        Returns a base64-encoded string containing nonce + ciphertext_with_tag.
        """
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)  # Standard 96-bit nonce for AES-GCM
        aad = f"{family_id}:{user_id}".encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, token.encode("utf-8"), aad)
        # Store as base64(nonce + ciphertext)
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("ascii")

    def decrypt_token(self, encrypted_payload: str, family_id: str, user_id: str) -> str | None:
        """
        Decrypts an encrypted refresh token from the grace stash.
        Validates the GCM authentication tag and AAD (family_id:user_id).
        """
        try:
            raw_bytes = base64.b64decode(encrypted_payload.encode("ascii"))
            if len(raw_bytes) < 12 + 16:  # 12-byte nonce + 16-byte tag minimum
                return None
            nonce = raw_bytes[:12]
            ciphertext = raw_bytes[12:]
            aad = f"{family_id}:{user_id}".encode("utf-8")
            aesgcm = AESGCM(self._key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, aad)
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.warning("Failed to decrypt grace stash envelope: %s", e)
            return None


crypto_service = GraceStashCrypto()
