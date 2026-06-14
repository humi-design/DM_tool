"""Security utilities."""

import secrets
import hashlib
import re
from typing import Optional

from argon2 import PasswordHasher

ph = PasswordHasher()


def hash_password(password: str, method: str = "argon2") -> str:
    """Hash a password using Argon2 or bcrypt."""
    if method == "argon2":
        return ph.hash(password)
    elif method == "bcrypt":
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    raise ValueError(f"Unknown hashing method: {method}")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    if not password_hash:
        return False
    
    if password_hash.startswith("$argon2"):
        try:
            return ph.verify(password_hash, password)
        except Exception:
            return False
    elif password_hash.startswith("$2"):
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False
    
    return False


def generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP."""
    return "".join([str(secrets.randbelow(10)) for _ in range(length)])


def hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate an API key."""
    return f"viraly_{secrets.token_urlsafe(32)}"


def check_password_strength(password: str) -> tuple[bool, list[str]]:
    """Check password strength and return validation result."""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data, showing only last few characters."""
    if not data or len(data) <= visible_chars:
        return "*" * len(data) if data else ""
    return "*" * (len(data) - visible_chars) + data[-visible_chars:]


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    filename = re.sub(r"[^\w\s.-]", "", filename)
    filename = re.sub(r"\s+", "_", filename)
    return filename