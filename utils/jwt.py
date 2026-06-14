"""JWT utilities for authentication."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from flask import current_app


class JWTManager:
    """JWT token management."""
    
    @staticmethod
    def create_access_token(
        user_id: str,
        organization_id: str = None,
        additional_claims: Dict[str, Any] = None,
    ) -> str:
        """Create a new JWT access token."""
        expires = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=15))
        
        payload = {
            "sub": user_id,
            "org": organization_id,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + expires,
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        secret = current_app.config["JWT_SECRET_KEY"]
        return jwt.encode(payload, secret, algorithm="HS256")
    
    @staticmethod
    def create_refresh_token(
        user_id: str,
        organization_id: str = None,
    ) -> str:
        """Create a new JWT refresh token."""
        expires = current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))
        
        payload = {
            "sub": user_id,
            "org": organization_id,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + expires,
        }
        
        secret = current_app.config["JWT_SECRET_KEY"]
        return jwt.encode(payload, secret, algorithm="HS256")
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            secret = current_app.config["JWT_SECRET_KEY"]
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify an access token."""
        payload = JWTManager.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None
    
    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify a refresh token."""
        payload = JWTManager.decode_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None
    
    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        """Extract user ID from a token."""
        payload = JWTManager.decode_token(token)
        return payload.get("sub") if payload else None
    
    @staticmethod
    def get_organization_from_token(token: str) -> Optional[str]:
        """Extract organization ID from a token."""
        payload = JWTManager.decode_token(token)
        return payload.get("org") if payload else None


def jwt_required(f):
    """Decorator to require valid JWT token."""
    from functools import wraps
    from flask import request, jsonify, g
    
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
        
        token = auth_header.split(" ")[1]
        payload = JWTManager.verify_access_token(token)
        
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        g.current_user_id = payload.get("sub")
        g.organization_id = payload.get("org")
        
        return f(*args, **kwargs)
    
    return decorated