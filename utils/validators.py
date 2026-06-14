"""Validators for user input."""

import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format."""
    if not email:
        return False, "Email is required"
    
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 255:
        return False, "Email is too long"
    
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 128:
        return False, "Password is too long"
    
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate phone number format."""
    if not phone:
        return True, ""
    
    pattern = r"^\+?[1-9]\d{1,14}$"
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    
    if not re.match(pattern, cleaned):
        return False, "Invalid phone number format"
    
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format."""
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 30:
        return False, "Username is too long"
    
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    return True, ""


def validate_url(url: str) -> Tuple[bool, str]:
    """Validate URL format."""
    if not url:
        return True, ""
    
    pattern = r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
    if not re.match(pattern, url):
        return False, "Invalid URL format"
    
    return True, ""


def validate_slug(slug: str) -> Tuple[bool, str]:
    """Validate slug format."""
    if not slug:
        return False, "Slug is required"
    
    if len(slug) < 2:
        return False, "Slug must be at least 2 characters"
    
    if len(slug) > 100:
        return False, "Slug is too long"
    
    if not re.match(r"^[a-z0-9-]+$", slug):
        return False, "Slug can only contain lowercase letters, numbers, and hyphens"
    
    return True, ""