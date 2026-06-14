"""Authentication models."""

from datetime import datetime, timedelta
import uuid
import hashlib
import secrets

from app import db


class RefreshToken(db.Model):
    """Refresh token model for JWT authentication with rotation."""
    
    __tablename__ = "refresh_tokens"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    token_family = db.Column(db.String(36), nullable=False, index=True)
    
    token_type = db.Column(db.String(50), default="refresh", nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    replaced_by = db.Column(db.String(36), nullable=True)
    replaced_by_token = db.Column(db.String(36), db.ForeignKey("refresh_tokens.id"), nullable=True)
    
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True, index=True)
    device_fingerprint = db.Column(db.String(64), nullable=True)
    
    is_revoked = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    
    __table_args__ = (
        db.Index("idx_token_family_created", "token_family", "created_at"),
        db.Index("idx_user_active_tokens", "user_id", "is_revoked", "is_used"),
    )
    
    def is_valid(self) -> bool:
        """Check if the token is valid."""
        if self.is_revoked or self.is_used:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def mark_used(self) -> None:
        """Mark token as used (part of rotation)."""
        self.is_used = True
        db.session.commit()
    
    def revoke(self, replaced_by: str = None) -> None:
        """Revoke the token."""
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()
        if replaced_by:
            self.replaced_by = replaced_by
        db.session.commit()
    
    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def generate_token(cls) -> tuple[str, str]:
        """Generate a new refresh token and its hash."""
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        return raw_token, token_hash
    
    @classmethod
    def create_token(
        cls,
        user_id: str,
        expires_delta: timedelta,
        user_agent: str = None,
        ip_address: str = None,
        device_fingerprint: str = None,
    ) -> tuple["RefreshToken", str]:
        """Create a new refresh token with rotation support."""
        raw_token, token_hash = cls.generate_token()
        token_family = str(uuid.uuid4())
        
        token = cls(
            user_id=user_id,
            token_hash=token_hash,
            token_family=token_family,
            expires_at=datetime.utcnow() + expires_delta,
            user_agent=user_agent,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
        )
        db.session.add(token)
        db.session.commit()
        return token, raw_token
    
    @classmethod
    def create_rotation_token(
        cls,
        old_token: "RefreshToken",
        expires_delta: timedelta,
    ) -> tuple["RefreshToken", str]:
        """Create a new token by rotating an existing valid token."""
        raw_token, token_hash = cls.generate_token()
        
        old_token.mark_used()
        old_token.revoke(replaced_by=token_hash)
        
        new_token = cls(
            user_id=old_token.user_id,
            token_hash=token_hash,
            token_family=old_token.token_family,
            expires_at=datetime.utcnow() + expires_delta,
            user_agent=old_token.user_agent,
            ip_address=old_token.ip_address,
            device_fingerprint=old_token.device_fingerprint,
            replaced_by_token=old_token.id,
        )
        db.session.add(new_token)
        db.session.commit()
        return new_token, raw_token
    
    @classmethod
    def find_by_hash(cls, token_hash: str) -> "RefreshToken":
        """Find token by its hash."""
        return cls.query.filter_by(token_hash=token_hash).first()
    
    @classmethod
    def revoke_family(cls, token_family: str, exclude_token_id: str = None) -> int:
        """Revoke all tokens in a family."""
        query = cls.query.filter(
            cls.token_family == token_family,
            cls.is_revoked == False,
        )
        if exclude_token_id:
            query = query.filter(cls.id != exclude_token_id)
        count = query.update(
            {"is_revoked": True, "revoked_at": datetime.utcnow()},
            synchronize_session=False,
        )
        db.session.commit()
        return count
    
    @classmethod
    def revoke_all_user_tokens(cls, user_id: str) -> int:
        """Revoke all tokens for a user."""
        count = cls.query.filter_by(
            user_id=user_id,
            is_revoked=False,
        ).update(
            {"is_revoked": True, "revoked_at": datetime.utcnow()},
            synchronize_session=False,
        )
        db.session.commit()
        return count


class LoginAttempt(db.Model):
    """Track login attempts for brute-force protection."""
    
    __tablename__ = "login_attempts"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    successful = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    failure_reason = db.Column(db.String(100), nullable=True)
    
    __table_args__ = (
        db.Index("idx_email_attempted", "email", "attempted_at"),
        db.Index("idx_ip_attempted", "ip_address", "attempted_at"),
    )
    
    @classmethod
    def record_attempt(
        cls,
        email: str,
        ip_address: str,
        successful: bool,
        user_id: str = None,
        user_agent: str = None,
        failure_reason: str = None,
    ) -> "LoginAttempt":
        """Record a login attempt."""
        attempt = cls(
            email=email,
            ip_address=ip_address,
            successful=successful,
            user_id=user_id,
            user_agent=user_agent,
            failure_reason=failure_reason,
        )
        db.session.add(attempt)
        db.session.commit()
        return attempt
    
    @classmethod
    def get_recent_attempts(cls, identifier: str, minutes: int = 15) -> list:
        """Get recent login attempts for email or IP."""
        since = datetime.utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.attempted_at >= since,
            db.or_(
                cls.email == identifier,
                cls.ip_address == identifier,
            ),
        ).order_by(cls.attempted_at.desc()).all()
    
    @classmethod
    def get_failed_count(cls, identifier: str, minutes: int = 15) -> int:
        """Get count of failed attempts."""
        since = datetime.utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.attempted_at >= since,
            cls.successful == False,
            db.or_(
                cls.email == identifier,
                cls.ip_address == identifier,
            ),
        ).count()


class PasswordResetToken(db.Model):
    """Password reset token model."""
    
    __tablename__ = "password_reset_tokens"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    
    @classmethod
    def generate_token(cls, user_id: str, expires_minutes: int = 60) -> tuple["PasswordResetToken", str]:
        """Generate a password reset token."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        token = cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
        )
        db.session.add(token)
        db.session.commit()
        return token, raw_token
    
    @classmethod
    def find_valid_by_hash(cls, token_hash: str) -> "PasswordResetToken":
        """Find a valid (not used, not expired) token by hash."""
        return cls.query.filter(
            cls.token_hash == token_hash,
            cls.is_used == False,
            cls.is_revoked == False,
            cls.expires_at > datetime.utcnow(),
        ).first()
    
    def mark_used(self, ip_address: str = None, user_agent: str = None) -> None:
        """Mark token as used."""
        self.is_used = True
        self.used_at = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
        db.session.commit()
    
    def revoke(self) -> None:
        """Revoke the token."""
        self.is_revoked = True
        db.session.commit()
    
    @classmethod
    def revoke_all_for_user(cls, user_id: str) -> int:
        """Revoke all unused tokens for a user."""
        count = cls.query.filter_by(
            user_id=user_id,
            is_used=False,
            is_revoked=False,
        ).update({"is_revoked": True}, synchronize_session=False)
        db.session.commit()
        return count


class OTPCode(db.Model):
    """OTP code model for multi-factor authentication."""
    
    __tablename__ = "otp_codes"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    code_hash = db.Column(db.String(64), nullable=False)
    
    code_type = db.Column(db.String(50), default="email", nullable=False)
    purpose = db.Column(db.String(50), default="verification", nullable=False)
    
    expires_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    attempts = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=5, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    ip_address = db.Column(db.String(45), nullable=True)
    destination = db.Column(db.String(255), nullable=True)
    
    __table_args__ = (
        db.Index("idx_user_purpose_active", "user_id", "purpose", "is_used", "is_verified"),
    )
    
    @classmethod
    def generate_otp(
        cls,
        user_id: str,
        code_type: str = "email",
        purpose: str = "verification",
        digits: int = 6,
        validity_minutes: int = 10,
        max_attempts: int = 5,
    ) -> tuple["OTPCode", str]:
        """Generate a new OTP code."""
        raw_code = "".join([str(secrets.randbelow(10)) for _ in range(digits)])
        code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
        
        cls.deactivate_previous(user_id, purpose)
        
        otp = cls(
            user_id=user_id,
            code_hash=code_hash,
            code_type=code_type,
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=validity_minutes),
            max_attempts=max_attempts,
        )
        db.session.add(otp)
        db.session.commit()
        return otp, raw_code
    
    @classmethod
    def deactivate_previous(cls, user_id: str, purpose: str) -> None:
        """Deactivate all previous OTPs for a purpose."""
        cls.query.filter(
            cls.user_id == user_id,
            cls.purpose == purpose,
            cls.is_used == False,
            cls.is_verified == False,
        ).update({"is_used": True}, synchronize_session=False)
        db.session.commit()
    
    def verify(self, raw_code: str) -> bool:
        """Verify the OTP code."""
        if self.is_used or self.is_verified:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if self.attempts >= self.max_attempts:
            return False
        
        code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
        if code_hash != self.code_hash:
            self.attempts += 1
            db.session.commit()
            return False
        
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        db.session.commit()
        return True
    
    def mark_used(self) -> None:
        """Mark OTP as used."""
        self.is_used = True
        db.session.commit()
    
    @classmethod
    def find_valid(cls, user_id: str, purpose: str) -> "OTPCode":
        """Find a valid OTP for a user and purpose."""
        return cls.query.filter(
            cls.user_id == user_id,
            cls.purpose == purpose,
            cls.is_used == False,
            cls.is_verified == True,
            cls.expires_at > datetime.utcnow(),
        ).first()


class EmailVerification(db.Model):
    """Email verification token model."""
    
    __tablename__ = "email_verifications"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    
    email = db.Column(db.String(255), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    verified_at = db.Column(db.DateTime, nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    ip_address = db.Column(db.String(45), nullable=True)
    
    @classmethod
    def generate_token(cls, user_id: str, email: str, expires_hours: int = 24) -> tuple["EmailVerification", str]:
        """Generate an email verification token."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        existing = cls.query.filter_by(user_id=user_id).first()
        if existing:
            existing.token_hash = token_hash
            existing.email = email
            existing.created_at = datetime.utcnow()
            existing.expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            existing.is_verified = False
            existing.verified_at = None
            db.session.commit()
            return existing, raw_token
        
        token = cls(
            user_id=user_id,
            token_hash=token_hash,
            email=email,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        )
        db.session.add(token)
        db.session.commit()
        return token, raw_token
    
    @classmethod
    def find_valid_by_hash(cls, token_hash: str) -> "EmailVerification":
        """Find a valid verification token."""
        return cls.query.filter(
            cls.token_hash == token_hash,
            cls.is_verified == False,
            cls.expires_at > datetime.utcnow(),
        ).first()
    
    def verify(self, ip_address: str = None) -> None:
        """Mark email as verified."""
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address
        db.session.commit()


class AuditLog(db.Model):
    """Audit log model for tracking user actions."""
    
    __tablename__ = "audit_logs"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    
    action = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    resource_type = db.Column(db.String(100), nullable=True, index=True)
    resource_id = db.Column(db.String(36), nullable=True)
    
    ip_address = db.Column(db.String(45), nullable=True, index=True)
    user_agent = db.Column(db.String(500), nullable=True)
    device_fingerprint = db.Column(db.String(64), nullable=True)
    
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    
    status = db.Column(db.String(50), default="success", nullable=False, index=True)
    error_message = db.Column(db.Text, nullable=True)
    error_code = db.Column(db.String(50), nullable=True)
    
    request_id = db.Column(db.String(36), nullable=True, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        db.Index("idx_user_action_created", "user_id", "action", "created_at"),
        db.Index("idx_action_created", "action", "created_at"),
        db.Index("idx_ip_created", "ip_address", "created_at"),
    )
    
    CATEGORY_AUTH = "authentication"
    CATEGORY_ACCOUNT = "account"
    CATEGORY_ORGANIZATION = "organization"
    CATEGORY_BUSINESS = "business"
    CATEGORY_INSTAGRAM = "instagram"
    CATEGORY_BILLING = "billing"
    CATEGORY_ADMIN = "admin"
    
    def to_dict(self) -> dict:
        """Convert audit log to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "action": self.action,
            "category": self.category,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def log(
        cls,
        action: str,
        category: str,
        user_id: str = None,
        organization_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success",
        error_message: str = None,
        error_code: str = None,
        old_values: dict = None,
        new_values: dict = None,
        request_id: str = None,
    ) -> "AuditLog":
        """Create an audit log entry."""
        log = cls(
            action=action,
            category=category,
            user_id=user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            error_code=error_code,
            old_values=old_values,
            new_values=new_values,
            request_id=request_id,
        )
        db.session.add(log)
        db.session.commit()
        return log


class UserSession(db.Model):
    """User session model for tracking active sessions."""
    
    __tablename__ = "user_sessions"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    session_token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    device_fingerprint = db.Column(db.String(64), nullable=True)
    
    device_type = db.Column(db.String(50), nullable=True)
    browser = db.Column(db.String(100), nullable=True)
    os = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_remember = db.Column(db.Boolean, default=False, nullable=False)
    
    @classmethod
    def create_session(
        cls,
        user_id: str,
        remember: bool = False,
        user_agent: str = None,
        ip_address: str = None,
        device_fingerprint: str = None,
    ) -> tuple["UserSession", str]:
        """Create a new user session."""
        raw_token = secrets.token_urlsafe(32)
        session_token = hashlib.sha256(raw_token.encode()).hexdigest()
        
        expires_days = 30 if remember else 7
        
        session = cls(
            user_id=user_id,
            session_token=session_token,
            user_agent=user_agent,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
            is_remember=remember,
        )
        
        cls.parse_user_agent(session, user_agent)
        
        db.session.add(session)
        db.session.commit()
        return session, raw_token
    
    @staticmethod
    def parse_user_agent(session: "UserSession", user_agent: str) -> None:
        """Parse user agent string to extract device info."""
        if not user_agent:
            return
        
        session.device_type = "Desktop"
        session.browser = "Unknown"
        session.os = "Unknown"
        
        ua_lower = user_agent.lower()
        
        if "mobile" in ua_lower or "android" in ua_lower and "mobile" in ua_lower:
            session.device_type = "Mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            session.device_type = "Tablet"
        
        if "chrome" in ua_lower and "edg" not in ua_lower:
            session.browser = "Chrome"
        elif "firefox" in ua_lower:
            session.browser = "Firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            session.browser = "Safari"
        elif "edg" in ua_lower:
            session.browser = "Edge"
        
        if "windows" in ua_lower:
            session.os = "Windows"
        elif "mac os" in ua_lower or "macos" in ua_lower:
            session.os = "macOS"
        elif "linux" in ua_lower and "android" not in ua_lower:
            session.os = "Linux"
        elif "android" in ua_lower:
            session.os = "Android"
        elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
            session.os = "iOS"
    
    def update_activity(self) -> None:
        """Update last active timestamp."""
        self.last_active_at = datetime.utcnow()
        db.session.commit()
    
    def revoke(self) -> None:
        """Revoke the session."""
        self.is_active = False
        db.session.commit()
    
    @classmethod
    def find_valid_by_token(cls, session_token: str) -> "UserSession":
        """Find a valid session by token."""
        token_hash = hashlib.sha256(session_token.encode()).hexdigest()
        return cls.query.filter(
            cls.session_token == token_hash,
            cls.is_active == True,
            cls.expires_at > datetime.utcnow(),
        ).first()
    
    @classmethod
    def get_user_sessions(cls, user_id: str, active_only: bool = True) -> list:
        """Get all sessions for a user."""
        query = cls.query.filter_by(user_id=user_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.last_active_at.desc()).all()
    
    @classmethod
    def revoke_all_user_sessions(cls, user_id: str, exclude_session_id: str = None) -> int:
        """Revoke all sessions for a user."""
        query = cls.query.filter_by(user_id=user_id, is_active=True)
        if exclude_session_id:
            query = query.filter(cls.id != exclude_session_id)
        count = query.update({"is_active": False}, synchronize_session=False)
        db.session.commit()
        return count