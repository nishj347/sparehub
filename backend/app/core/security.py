"""Security utilities for password hashing and verification using Argon2id."""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Pre-computed dummy Argon2id hash used to perform dummy password verification
# when an account is not found, ensuring uniform response times to prevent account enumeration.
DUMMY_PASSWORD_HASH = _hasher.hash("dummy_constant_time_precomputed_password_check")


def hash_password(plain: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Check if the stored Argon2id hash needs rehashing due to parameter updates."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except Exception:
        return True
