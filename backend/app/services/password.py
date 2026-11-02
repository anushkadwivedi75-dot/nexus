import logging
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

logger = logging.getLogger(__name__)

# Argon2id hasher calibrated to OWASP / Blueprint v1.3.1 parameters
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# Pre-computed dummy hash to mitigate timing side-channel attacks on non-existent users
_DUMMY_HASH = ph.hash("NexusDummyPasswordForTimingMitigation123!")


class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes a plaintext password using Argon2id. Plaintext is never logged."""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return ph.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plaintext password against an Argon2id hash in constant time."""
        if not plain_password or not hashed_password:
            return False
        try:
            return ph.verify(hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        except Exception as e:
            logger.error("Unexpected error during password verification: %s", type(e).__name__)
            return False

    @staticmethod
    def verify_dummy():
        """Performs a constant-time dummy verification when user is not found."""
        try:
            ph.verify(_DUMMY_HASH, "NexusDummyPasswordForTimingMitigation123!")
        except Exception:
            pass


password_service = PasswordService()

