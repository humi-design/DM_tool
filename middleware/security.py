"""Security middleware."""

import re
from typing import Callable

from flask import Flask, request, g
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
        g.request_id = request.headers.get("X-Request-ID", generate_request_id())
        
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            content_type = request.content_type or ""
            if "application/json" in content_type:
                pass
    
    def process_response(self, response: Response) -> Response:
        """Process outgoing response."""
        response.headers["X-Request-ID"] = g.get("request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Max-Age"] = "3600"
        
        return response


def generate_request_id() -> str:
    """Generate a unique request ID."""
    import uuid
    return str(uuid.uuid4())


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
        from flask import abort
        
        client_ip = request.remote_addr
        if client_ip in self.blacklist:
            abort(403)
    
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
        allowed_tags = bleach.ALLOWED_TAGS + ["p", "br", "ul", "ol", "li", "strong", "em"]
        return bleach.clean(text, tags=allowed_tags, attributes={}, strip=True)
    
    @staticmethod
    def sanitize_sql(text: str) -> str:
        """Sanitize input for SQL (parameterized queries handle this, but as backup)."""
        if not text:
            return text
        dangerous_patterns = [
            r"(\b(OR|AND)\b.*\b(=|>|<|!)\b)",
            r"(--|\/\*|\*\/)",
            r"(UNION|SELECT|INSERT|UPDATE|DELETE|DROP)\b",
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