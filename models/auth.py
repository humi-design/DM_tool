"""Authentication models."""

from datetime import datetime, timedelta
import uuid

from app import db


class RefreshToken(db.Model):
    """Refresh token model for JWT authentication."""
    
    __tablename__ = "refresh_tokens"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    
    token_hash = db.Column(db.String(255), nullable=False, index=True)
    token_type = db.Column(db.String(50), default="refresh", nullable=False)
    
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    replaced_by = db.Column(db.String(36), nullable=True)
    
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    
    def is_valid(self) -> bool:
        """Check if the token is valid."""
        if self.is_revoked:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def revoke(self, replaced_by: str = None) -> None:
        """Revoke the token."""
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()
        if replaced_by:
            self.replaced_by = replaced_by
        db.session.commit()
    
    @classmethod
    def create_token(cls, user_id: str, expires_delta: timedelta, **kwargs) -> "RefreshToken":
        """Create a new refresh token."""
        token = cls(
            user_id=user_id,
            expires_at=datetime.utcnow() + expires_delta,
            **kwargs
        )
        db.session.add(token)
        db.session.commit()
        return token
    
    @classmethod
    def revoke_all_user_tokens(cls, user_id: str) -> None:
        """Revoke all tokens for a user."""
        cls.query.filter_by(user_id=user_id, is_revoked=False).update(
            {"is_revoked": True, "revoked_at": datetime.utcnow()}
        )
        db.session.commit()


class AuditLog(db.Model):
    """Audit log model for tracking user actions."""
    
    __tablename__ = "audit_logs"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=True)
    
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(100), nullable=True, index=True)
    resource_id = db.Column(db.String(36), nullable=True)
    
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    
    status = db.Column(db.String(50), default="success", nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        """Convert audit log to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LoginAttempt(db.Model):
    """Track login attempts for security."""
    
    __tablename__ = "login_attempts"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    successful = db.Column(db.Boolean, default=False, nullable=False)
    
    failure_reason = db.Column(db.String(100), nullable=True)


class OTPCode(db.Model):
    """OTP code model for multi-factor authentication."""
    
    __tablename__ = "otp_codes"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    
    code_hash = db.Column(db.String(255), nullable=False)
    code_type = db.Column(db.String(50), default="email", nullable=False)
    purpose = db.Column(db.String(50), default="verification", nullable=False)
    
    expires_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    def is_valid(self, code: str, max_attempts: int = 3) -> bool:
        """Check if OTP is valid."""
        if self.is_used or self.is_verified:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if self.attempts >= max_attempts:
            return False
        
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        try:
            return ph.verify(self.code_hash, code)
        except Exception:
            return False
    
    def mark_verified(self) -> None:
        """Mark OTP as verified."""
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        db.session.commit()
    
    def mark_used(self) -> None:
        """Mark OTP as used."""
        self.is_used = True
        db.session.commit()
    
    def increment_attempts(self) -> None:
        """Increment failed attempts."""
        self.attempts += 1
        db.session.commit()