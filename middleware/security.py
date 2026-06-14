"""Security middleware."""

import re
from typing import Callable, Optional
import secrets
import hashlib

from flask import Flask, request, g, make_response, jsonify
from flask.wrappers import Response


class SecurityMiddleware:
    """Security middleware for request/response processing."""
    
    def __init__(self, app: Flask = None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize the middleware."""
        app.before_request(self.process_request)
        app.after_request(self.process_response)
    
    def process_request(self) -> None:
        """Process incoming request."""
        from utils.jwt import get_client_ip, get_user_agent, get_device_fingerprint
        
        g.request_id = request.headers.get("X-Request-ID", _generate_request_id())
        g.client_ip = get_client_ip()
        g.user_agent = get_user_agent()
        g.device_fingerprint = get_device_fingerprint()
        
        g.request_start_time = _get_timestamp()
    
    def process_response(self, response: Response) -> Response:
        """Process outgoing response."""
        response.headers["X-Request-ID"] = g.get("request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'"
        
        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRFToken, X-Requested-With, X-Session-Token"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
        
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


class IPBlacklistMiddleware:
    """Middleware to block requests from blacklisted IPs."""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.blacklist = set()
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize the middleware."""
        app.before_request(self.check_ip)
    
    def check_ip(self) -> None:
        """Check if IP is blacklisted."""
        from services.auth_service import AuthError
        
        client_ip = g.get("client_ip") or request.remote_addr
        if client_ip in self.blacklist:
            raise AuthError("Access denied", code="ip_blocked", status_code=403)
    
    def add_to_blacklist(self, ip: str) -> None:
        """Add IP to blacklist."""
        self.blacklist.add(ip)
    
    def remove_from_blacklist(self, ip: str) -> None:
        """Remove IP from blacklist."""
        self.blacklist.discard(ip)


class InputSanitizer:
    """Input sanitizer for XSS prevention."""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Remove potentially dangerous HTML."""
        import bleach
        allowed_tags = []
        allowed_attributes = {}
        return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    
    @staticmethod
    def sanitize_sql(text: str) -> str:
        """Sanitize input for SQL (parameterized queries handle this, but as backup)."""
        if not text:
            return text
        dangerous_patterns = [
            r"(\b(OR|AND)\b.*\b(=|>|<|!)\b)",
            r"(--|\/\*|\*\/)",
            r"(UNION|SELECT|INSERT|UPDATE|DELETE|DROP)\b",
            r";\s*(DROP|DELETE|TRUNCATE)\s+",
        ]
        for pattern in dangerous_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return text
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        pattern = r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
        return bool(re.match(pattern, url))


class SecureHeaders:
    """Add secure headers to responses."""
    
    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "X-Permitted-Cross-Domain-Policies": "none",
        "X-Download-Options": "noopen",
        "X-DNS-Prefetch-Control": "on",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    
    @classmethod
    def add_headers(cls, response: Response) -> Response:
        """Add secure headers to response."""
        for header, value in cls.HEADERS.items():
            response.headers[header] = value
        return response


def _generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(secrets.token_urlsafe(16))


def _get_timestamp() -> float:
    """Get current timestamp."""
    import time
    return time.time()


def rate_limit_key() -> str:
    """Generate a rate limit key based on IP and user."""
    from flask import request
    from utils.jwt import get_current_user_id
    
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_id = get_current_user_id()
    
    if user_id:
        return f"user:{user_id}"
    return f"ip:{ip}"