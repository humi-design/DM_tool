"""JWT utilities for authentication."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

import jwt
from flask import current_app, request, g


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class JWTManager:
    """JWT token management with enhanced features."""
    
    @classmethod
    def create_access_token(
        cls,
        user_id: str,
        organization_id: str = None,
        additional_claims: Dict[str, Any] = None,
        expires_delta: timedelta = None,
    ) -> str:
        """Create a new JWT access token."""
        if expires_delta is None:
            expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=15))
        
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "org": organization_id,
            "type": "access",
            "iat": now,
            "nbf": now,
            "exp": now + expires_delta,
            "jti": cls._generate_jti(),
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        secret = current_app.config["JWT_SECRET_KEY"]
        return jwt.encode(payload, secret, algorithm="HS256")
    
    @classmethod
    def create_refresh_token(
        cls,
        user_id: str,
        organization_id: str = None,
        expires_delta: timedelta = None,
    ) -> str:
        """Create a new JWT refresh token."""
        if expires_delta is None:
            expires_delta = current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))
        
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "org": organization_id,
            "type": "refresh",
            "iat": now,
            "nbf": now,
            "exp": now + expires_delta,
            "jti": cls._generate_jti(),
        }
        
        secret = current_app.config["JWT_SECRET_KEY"]
        return jwt.encode(payload, secret, algorithm="HS256")
    
    @classmethod
    def decode_token(cls, token: str, verify: bool = True) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            secret = current_app.config["JWT_SECRET_KEY"]
            options = {"verify_signature": verify, "verify_exp": verify, "verify_nbf": verify}
            payload = jwt.decode(token, secret, algorithms=["HS256"], options=options)
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @classmethod
    def verify_access_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Verify an access token."""
        payload = cls.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None
    
    @classmethod
    def verify_refresh_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Verify a refresh token."""
        payload = cls.decode_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None
    
    @classmethod
    def get_user_id_from_token(cls, token: str) -> Optional[str]:
        """Extract user ID from a token."""
        payload = cls.decode_token(token)
        return payload.get("sub") if payload else None
    
    @classmethod
    def get_organization_from_token(cls, token: str) -> Optional[str]:
        """Extract organization ID from a token."""
        payload = cls.decode_token(token)
        return payload.get("org") if payload else None
    
    @classmethod
    def get_jti_from_token(cls, token: str) -> Optional[str]:
        """Extract JTI (JWT ID) from a token."""
        payload = cls.decode_token(token)
        return payload.get("jti") if payload else None
    
    @staticmethod
    def _generate_jti() -> str:
        """Generate a unique JWT ID."""
        import secrets
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def _JSONEncoder(obj: Any) -> str:
        """Custom JSON encoder for datetime."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def jwt_required(f):
    """Decorator to require valid JWT token."""
    from functools import wraps
    
    @wraps(f)
    def decorated(*args, **kwargs):
        from services.auth_service import AuthError
        from models.auth import UserSession
        
        auth_header = request.headers.get("Authorization", "")
        token = None
        
        # Check for token in Authorization header first
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        # Fall back to access_token cookie for browser sessions
        elif request.cookies.get("access_token"):
            token = request.cookies.get("access_token")
        
        if not token:
            raise AuthError("Missing or invalid authorization header", code="missing_token", status_code=401)
        
        payload = JWTManager.verify_access_token(token)
        
        if not payload:
            raise AuthError("Invalid or expired token", code="invalid_token", status_code=401)
        
        g.current_user_id = payload.get("sub")
        g.organization_id = payload.get("org")
        g.access_token = token
        g.token_jti = payload.get("jti")
        
        # Check session token from header or cookie
        session_token = request.headers.get("X-Session-Token") or request.cookies.get("session_token")
        if session_token:
            session = UserSession.find_valid_by_token(session_token)
            if session:
                session.update_activity()
                g.current_session = session
        
        return f(*args, **kwargs)
    
    return decorated


def jwt_optional(f):
    """Decorator for optional JWT authentication."""
    from functools import wraps
    
    @wraps(f)
    def decorated(*args, **kwargs):
        g.current_user_id = None
        g.organization_id = None
        
        auth_header = request.headers.get("Authorization", "")
        token = None
        
        # Check for token in Authorization header first
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        # Fall back to access_token cookie for browser sessions
        elif request.cookies.get("access_token"):
            token = request.cookies.get("access_token")
        
        if token:
            payload = JWTManager.verify_access_token(token)
            if payload:
                g.current_user_id = payload.get("sub")
                g.organization_id = payload.get("org")
        
        return f(*args, **kwargs)
    
    return decorated


def get_current_user_id() -> Optional[str]:
    """Get the current user ID from the request context."""
    return getattr(g, "current_user_id", None)


def get_current_organization_id() -> Optional[str]:
    """Get the current organization ID from the request context."""
    return getattr(g, "organization_id", None)


def get_client_ip() -> str:
    """Get the client IP address, considering proxy headers."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    return request.remote_addr


def get_user_agent() -> str:
    """Get the user agent string from the request."""
    return request.headers.get("User-Agent", "")[:500]


def get_device_fingerprint() -> str:
    """Get a device fingerprint from request headers."""
    import hashlib
    
    components = [
        request.headers.get("User-Agent", ""),
        request.headers.get("Accept-Language", ""),
        request.headers.get("Accept-Encoding", ""),
        get_client_ip(),
    ]
    
    fingerprint = "|".join(components)
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:64]