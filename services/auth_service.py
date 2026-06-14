"""Authentication service for user authentication."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple

from argon2 import PasswordHasher
from flask import current_app

from app import db
from models.user import User
from models.auth import (
    RefreshToken,
    LoginAttempt,
    PasswordResetToken,
    EmailVerification,
    OTPCode,
    UserSession,
)
from models.audit_log import AuditLog
from utils.jwt import JWTManager


ph = PasswordHasher()


class AuthError(Exception):
    """Base authentication error."""
    
    def __init__(self, message: str, code: str = "auth_error", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class RateLimitError(AuthError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str = "Too many attempts. Please try again later."):
        super().__init__(message, code="rate_limit_exceeded", status_code=429)


class InvalidCredentialsError(AuthError):
    """Invalid credentials error."""
    
    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(message, code="invalid_credentials", status_code=401)


class AccountLockedError(AuthError):
    """Account locked error."""
    
    def __init__(self, message: str = "Account is temporarily locked.", retry_after: int = 900):
        self.retry_after = retry_after
        super().__init__(message, code="account_locked", status_code=423)


@dataclass
class AuthResult:
    """Authentication result container."""
    success: bool
    user: Optional[User] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    session_token: Optional[str] = None
    requires_verification: bool = False
    verification_method: Optional[str] = None
    message: Optional[str] = None


class AuthService:
    """Service for handling authentication operations."""
    
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    @classmethod
    def register(
        cls,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthResult:
        """Register a new user account."""
        if User.query.filter_by(email=email.lower()).first():
            raise AuthError("Email already registered", code="email_exists", status_code=409)
        
        user = User(
            email=email.lower().strip(),
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        verification, raw_token = EmailVerification.generate_token(user.id, user.email)
        
        AuditLog.log(
            action="user_registered",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            new_values={"email": user.email},
        )
        
        return AuthResult(
            success=True,
            user=user,
            requires_verification=True,
            verification_method="email",
            message="Registration successful. Please verify your email.",
        )
    
    @classmethod
    def login(
        cls,
        email: str,
        password: str,
        remember: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
    ) -> AuthResult:
        """Authenticate a user and create a session."""
        email = email.lower().strip()
        
        cls._check_rate_limit(email, ip_address)
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.verify_password(password):
            cls._record_failed_login(email, ip_address, user_agent, "invalid_password")
            raise InvalidCredentialsError()
        
        if not user.is_active:
            cls._record_failed_login(email, ip_address, user_agent, "account_inactive")
            raise AuthError("Account is deactivated", code="account_inactive", status_code=403)
        
        if not user.is_verified and current_app.config.get("REQUIRE_EMAIL_VERIFICATION", True):
            verification, raw_token = EmailVerification.generate_token(user.id, user.email)
            cls._record_failed_login(email, ip_address, user_agent, "email_not_verified")
            raise AuthError(
                "Please verify your email first",
                code="email_not_verified",
                status_code=403,
            )
        
        access_token = JWTManager.create_access_token(user.id)
        refresh_token_obj, raw_refresh_token = RefreshToken.create_token(
            user_id=user.id,
            expires_delta=current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30)),
            user_agent=user_agent,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
        )
        
        session, raw_session_token = UserSession.create_session(
            user_id=user.id,
            remember=remember,
            user_agent=user_agent,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
        )
        
        user.update_last_login(ip_address)
        
        LoginAttempt.record_attempt(
            email=email,
            ip_address=ip_address,
            successful=True,
            user_id=user.id,
            user_agent=user_agent,
        )
        
        AuditLog.log(
            action="user_login",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            new_values={"device_type": session.device_type, "browser": session.browser},
        )
        
        return AuthResult(
            success=True,
            user=user,
            access_token=access_token,
            refresh_token=raw_refresh_token,
            session_token=raw_session_token,
        )
    
    @classmethod
    def logout(
        cls,
        user_id: str,
        session_id: Optional[str] = None,
        all_sessions: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Logout user and revoke sessions/tokens."""
        if all_sessions:
            RefreshToken.revoke_all_user_tokens(user_id)
            UserSession.revoke_all_user_sessions(user_id)
        elif session_id:
            session = UserSession.query.get(session_id)
            if session:
                session.revoke()
        
        AuditLog.log(
            action="user_logout",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return True
    
    @classmethod
    def refresh_tokens(
        cls,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthResult:
        """Refresh access and refresh tokens with rotation."""
        token_hash = cls._hash_token(refresh_token)
        stored_token = RefreshToken.find_by_hash(token_hash)
        
        if not stored_token or not stored_token.is_valid():
            raise InvalidCredentialsError("Invalid or expired refresh token")
        
        user = User.query.get(stored_token.user_id)
        if not user or not user.is_active:
            raise AuthError("User not found or inactive", code="user_inactive", status_code=401)
        
        new_access_token = JWTManager.create_access_token(user.id)
        
        new_token_obj, raw_new_refresh = RefreshToken.create_rotation_token(
            old_token=stored_token,
            expires_delta=current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30)),
        )
        
        stored_token.update_last_used()
        
        AuditLog.log(
            action="token_refreshed",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return AuthResult(
            success=True,
            user=user,
            access_token=new_access_token,
            refresh_token=raw_new_refresh,
        )
    
    @classmethod
    def request_password_reset(
        cls,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Request a password reset for an email."""
        user = User.query.filter_by(email=email.lower()).first()
        
        if user:
            PasswordResetToken.revoke_all_for_user(user.id)
            
            reset_token, raw_token = PasswordResetToken.generate_token(user.id)
            
            AuditLog.log(
                action="password_reset_requested",
                category=AuditLog.CATEGORY_AUTH,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        
        return True
    
    @classmethod
    def reset_password(
        cls,
        token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Reset password using a valid reset token."""
        token_hash = cls._hash_token(token)
        reset_token = PasswordResetToken.find_valid_by_hash(token_hash)
        
        if not reset_token:
            raise AuthError("Invalid or expired reset token", code="invalid_token", status_code=400)
        
        user = User.query.get(reset_token.user_id)
        if not user:
            raise AuthError("User not found", code="user_not_found", status_code=404)
        
        user.set_password(new_password)
        reset_token.mark_used(ip_address=ip_address, user_agent=user_agent)
        
        PasswordResetToken.revoke_all_for_user(user.id)
        RefreshToken.revoke_all_user_tokens(user.id)
        UserSession.revoke_all_user_sessions(user.id)
        
        AuditLog.log(
            action="password_reset_complete",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return True
    
    @classmethod
    def verify_email(
        cls,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Verify email using a verification token."""
        token_hash = cls._hash_token(token)
        verification = EmailVerification.find_valid_by_hash(token_hash)
        
        if not verification:
            raise AuthError("Invalid or expired verification token", code="invalid_token", status_code=400)
        
        user = User.query.get(verification.user_id)
        if not user:
            raise AuthError("User not found", code="user_not_found", status_code=404)
        
        verification.verify(ip_address=ip_address)
        user.is_verified = True
        user.email_verified_at = db.func.now()
        db.session.commit()
        
        AuditLog.log(
            action="email_verified",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return True
    
    @classmethod
    def resend_verification(
        cls,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Resend email verification."""
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user:
            return True
        
        if user.is_verified:
            return True
        
        EmailVerification.generate_token(user.id, user.email)
        
        AuditLog.log(
            action="verification_resent",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return True
    
    @classmethod
    def request_email_otp(
        cls,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Generate and return email OTP (in real app, send via email)."""
        user = User.query.get(user_id)
        if not user:
            raise AuthError("User not found", code="user_not_found", status_code=404)
        
        otp, raw_code = OTPCode.generate_otp(
            user_id=user_id,
            code_type="email",
            purpose="login_verification",
            digits=6,
            validity_minutes=10,
        )
        
        AuditLog.log(
            action="otp_email_requested",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return raw_code
    
    @classmethod
    def request_sms_otp(
        cls,
        user_id: str,
        phone: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Generate and send SMS OTP (in real app, send via SMS provider)."""
        user = User.query.get(user_id)
        if not user:
            raise AuthError("User not found", code="user_not_found", status_code=404)
        
        otp, raw_code = OTPCode.generate_otp(
            user_id=user_id,
            code_type="sms",
            purpose="login_verification",
            digits=6,
            validity_minutes=5,
        )
        otp.destination = phone
        
        AuditLog.log(
            action="otp_sms_requested",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return True
    
    @classmethod
    def verify_otp(
        cls,
        user_id: str,
        code: str,
        purpose: str = "login_verification",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthResult:
        """Verify an OTP code."""
        valid_otp = OTPCode.find_valid(user_id, purpose)
        
        if not valid_otp:
            raise AuthError("No valid OTP found", code="invalid_otp", status_code=400)
        
        if not valid_otp.verify(code):
            raise AuthError("Invalid or expired OTP", code="invalid_otp", status_code=400)
        
        user = User.query.get(user_id)
        if not user:
            raise AuthError("User not found", code="user_not_found", status_code=404)
        
        valid_otp.mark_used()
        
        access_token = JWTManager.create_access_token(user.id)
        refresh_token_obj, raw_refresh_token = RefreshToken.create_token(
            user_id=user.id,
            expires_delta=current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30)),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        
        AuditLog.log(
            action="otp_verified",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return AuthResult(
            success=True,
            user=user,
            access_token=access_token,
            refresh_token=raw_refresh_token,
        )
    
    @classmethod
    def get_user_sessions(cls, user_id: str) -> list:
        """Get all active sessions for a user."""
        return UserSession.get_user_sessions(user_id)
    
    @classmethod
    def revoke_session(cls, user_id: str, session_id: str) -> bool:
        """Revoke a specific session."""
        session = UserSession.query.filter_by(id=session_id, user_id=user_id).first()
        if session:
            session.revoke()
            return True
        return False
    
    @classmethod
    def _check_rate_limit(cls, email: str, ip_address: str = None) -> None:
        """Check if login attempts are rate limited."""
        failed_by_email = LoginAttempt.get_failed_count(email, minutes=cls.LOCKOUT_DURATION_MINUTES)
        
        if failed_by_email >= cls.MAX_LOGIN_ATTEMPTS:
            raise AccountLockedError(retry_after=cls.LOCKOUT_DURATION_MINUTES * 60)
        
        if ip_address:
            failed_by_ip = LoginAttempt.get_failed_count(ip_address, minutes=cls.LOCKOUT_DURATION_MINUTES)
            if failed_by_ip >= cls.MAX_LOGIN_ATTEMPTS * 2:
                raise AccountLockedError(retry_after=cls.LOCKOUT_DURATION_MINUTES * 60)
    
    @classmethod
    def _record_failed_login(
        cls,
        email: str,
        ip_address: str,
        user_agent: str,
        reason: str,
    ) -> None:
        """Record a failed login attempt."""
        user = User.query.filter_by(email=email).first()
        LoginAttempt.record_attempt(
            email=email,
            ip_address=ip_address,
            successful=False,
            user_id=user.id if user else None,
            user_agent=user_agent,
            failure_reason=reason,
        )
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage/comparison."""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()


class GoogleOAuthService:
    """Service for Google OAuth integration."""
    
    @classmethod
    def get_authorization_url(cls, redirect_uri: str, state: str = None) -> str:
        """Get Google OAuth authorization URL."""
        import secrets
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": current_app.config.get("GOOGLE_CLIENT_ID"),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        
        import urllib.parse
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    @classmethod
    def exchange_code_for_tokens(cls, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for tokens."""
        import requests
        
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": current_app.config.get("GOOGLE_CLIENT_ID"),
                "client_secret": current_app.config.get("GOOGLE_CLIENT_SECRET"),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        
        if response.status_code != 200:
            raise AuthError("Failed to exchange code for tokens", code="oauth_error")
        
        return response.json()
    
    @classmethod
    def get_user_info(cls, access_token: str) -> dict:
        """Get user info from Google."""
        import requests
        
        response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            raise AuthError("Failed to get user info", code="oauth_error")
        
        return response.json()
    
    @classmethod
    def authenticate_or_register(
        cls,
        google_user: dict,
        ip_address: str = None,
        user_agent: str = None,
    ) -> AuthResult:
        """Authenticate or register user via Google OAuth."""
        email = google_user.get("email", "").lower()
        
        if not email:
            raise AuthError("Email not provided by Google", code="oauth_error")
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(
                email=email,
                first_name=google_user.get("given_name"),
                last_name=google_user.get("family_name"),
                avatar_url=google_user.get("picture"),
                is_verified=True,
            )
            db.session.add(user)
            db.session.commit()
            
            AuditLog.log(
                action="user_registered_google",
                category=AuditLog.CATEGORY_AUTH,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                new_values={"email": email},
            )
        
        access_token = JWTManager.create_access_token(user.id)
        refresh_token_obj, raw_refresh_token = RefreshToken.create_token(
            user_id=user.id,
            expires_delta=current_app.config.get("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30)),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        
        user.update_last_login(ip_address)
        
        AuditLog.log(
            action="user_login_google",
            category=AuditLog.CATEGORY_AUTH,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return AuthResult(
            success=True,
            user=user,
            access_token=access_token,
            refresh_token=raw_refresh_token,
        )