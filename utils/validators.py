"""Validators for user input."""

import re
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Validation result container."""
    is_valid: bool
    error: Optional[str] = None
    errors: Optional[list] = None


def validate_email(email: str) -> ValidationResult:
    """Validate email format."""
    if not email:
        return ValidationResult(False, error="Email is required")
    
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return ValidationResult(False, error="Invalid email format")
    
    if len(email) > 255:
        return ValidationResult(False, error="Email is too long")
    
    return ValidationResult(True)


def validate_password(password: str, min_length: int = 8) -> ValidationResult:
    """Validate password strength."""
    if not password:
        return ValidationResult(False, error="Password is required")
    
    errors = []
    
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")
    
    if len(password) > 128:
        return ValidationResult(False, error="Password is too long")
    
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        errors.append("Password must contain at least one special character")
    
    if errors:
        return ValidationResult(False, errors=errors)
    
    return ValidationResult(True)


def validate_password_confirmation(password: str, confirmation: str) -> ValidationResult:
    """Validate password confirmation matches."""
    if password != confirmation:
        return ValidationResult(False, error="Passwords do not match")
    return ValidationResult(True)


def validate_phone(phone: str) -> ValidationResult:
    """Validate phone number format."""
    if not phone:
        return ValidationResult(True)
    
    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone)
    
    if not re.match(r"^\+?[1-9]\d{1,14}$", cleaned):
        return ValidationResult(False, error="Invalid phone number format")
    
    if len(cleaned) < 10 or len(cleaned) > 15:
        return ValidationResult(False, error="Phone number must be 10-15 digits")
    
    return ValidationResult(True)


def validate_username(username: str) -> ValidationResult:
    """Validate username format."""
    if not username:
        return ValidationResult(False, error="Username is required")
    
    if len(username) < 3:
        return ValidationResult(False, error="Username must be at least 3 characters")
    
    if len(username) > 30:
        return ValidationResult(False, error="Username is too long")
    
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return ValidationResult(False, error="Username can only contain letters, numbers, underscores, and hyphens")
    
    return ValidationResult(True)


def validate_url(url: str) -> ValidationResult:
    """Validate URL format."""
    if not url:
        return ValidationResult(True)
    
    pattern = r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
    if not re.match(pattern, url):
        return ValidationResult(False, error="Invalid URL format")
    
    return ValidationResult(True)


def validate_slug(slug: str) -> ValidationResult:
    """Validate slug format."""
    if not slug:
        return ValidationResult(False, error="Slug is required")
    
    if len(slug) < 2:
        return ValidationResult(False, error="Slug must be at least 2 characters")
    
    if len(slug) > 100:
        return ValidationResult(False, error="Slug is too long")
    
    if not re.match(r"^[a-z0-9-]+$", slug):
        return ValidationResult(False, error="Slug can only contain lowercase letters, numbers, and hyphens")
    
    return ValidationResult(True)


def validate_otp_code(code: str, digits: int = 6) -> ValidationResult:
    """Validate OTP code format."""
    if not code:
        return ValidationResult(False, error="OTP code is required")
    
    if not re.match(r"^\d+$", code):
        return ValidationResult(False, error="OTP code must contain only digits")
    
    if len(code) != digits:
        return ValidationResult(False, error=f"OTP code must be {digits} digits")
    
    return ValidationResult(True)


def validate_name(name: str, field: str = "Name", min_length: int = 1, max_length: int = 100) -> ValidationResult:
    """Validate name field."""
    if not name:
        if min_length > 0:
            return ValidationResult(False, error=f"{field} is required")
        return ValidationResult(True)
    
    name = name.strip()
    
    if len(name) < min_length:
        return ValidationResult(False, error=f"{field} is too short")
    
    if len(name) > max_length:
        return ValidationResult(False, error=f"{field} is too long")
    
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        return ValidationResult(False, error=f"{field} contains invalid characters")
    
    return ValidationResult(True)


def sanitize_input(value: str) -> str:
    """Sanitize user input to prevent XSS."""
    if not value:
        return value
    
    import bleach
    return bleach.clean(value, tags=[], strip=True)