"""Tests for authentication module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import hashlib
import secrets

from app import create_app, db
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
from services.auth_service import (
    AuthService,
    AuthError,
    InvalidCredentialsError,
    RateLimitError,
    AccountLockedError,
    AuthResult,
    GoogleOAuthService,
)
from utils.validators import (
    validate_email,
    validate_password,
    validate_phone,
    validate_username,
    validate_otp_code,
    validate_name,
    ValidationResult,
)
from utils.jwt import JWTManager


@pytest.fixture
def app():
    """Create test application."""
    app = create_app("testing")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "JWT_SECRET_KEY": "test-secret-key",
        "JWT_ACCESS_TOKEN_EXPIRES": timedelta(minutes=15),
        "JWT_REFRESH_TOKEN_EXPIRES": timedelta(days=30),
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create test user."""
    from models.user import User
    from app import db
    with app.app_context():
        user = User(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_verified=True,
        )
        user.set_password("TestPassword123!")
        db.session.add(user)
        db.session.commit()
        return user.id


class TestValidators:
    """Test validation functions."""
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        result = validate_email("user@example.com")
        assert result.is_valid is True
        assert result.error is None
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        result = validate_email("invalid-email")
        assert result.is_valid is False
        assert result.error is not None
    
    def test_validate_email_empty(self):
        """Test empty email validation."""
        result = validate_email("")
        assert result.is_valid is False
    
    def test_validate_password_valid(self):
        """Test valid password validation."""
        result = validate_password("StrongPass123!")
        assert result.is_valid is True
    
    def test_validate_password_too_short(self):
        """Test password too short."""
        result = validate_password("Short1!")
        assert result.is_valid is False
    
    def test_validate_password_no_uppercase(self):
        """Test password without uppercase."""
        result = validate_password("nouppercase123!")
        assert result.is_valid is False
    
    def test_validate_password_no_special(self):
        """Test password without special char."""
        result = validate_password("NoSpecialChar123")
        assert result.is_valid is False
    
    def test_validate_phone_valid(self):
        """Test valid phone validation."""
        result = validate_phone("+1234567890")
        assert result.is_valid is True
    
    def test_validate_phone_invalid(self):
        """Test invalid phone validation."""
        result = validate_phone("abc123")
        assert result.is_valid is False
    
    def test_validate_username_valid(self):
        """Test valid username validation."""
        result = validate_username("valid_user")
        assert result.is_valid is True
    
    def test_validate_username_too_short(self):
        """Test username too short."""
        result = validate_username("ab")
        assert result.is_valid is False
    
    def test_validate_username_invalid_chars(self):
        """Test username with invalid characters."""
        result = validate_username("user@name")
        assert result.is_valid is False
    
    def test_validate_otp_code_valid(self):
        """Test valid OTP code."""
        result = validate_otp_code("123456")
        assert result.is_valid is True
    
    def test_validate_otp_code_wrong_length(self):
        """Test OTP code wrong length."""
        result = validate_otp_code("12345")
        assert result.is_valid is False
    
    def test_validate_name_valid(self):
        """Test valid name."""
        result = validate_name("John")
        assert result.is_valid is True
    
    def test_validate_name_with_space(self):
        """Test name with space."""
        result = validate_name("Mary Jane")
        assert result.is_valid is True
    
    def test_validate_name_with_apostrophe(self):
        """Test name with apostrophe."""
        result = validate_name("O'Brien")
        assert result.is_valid is True


class TestJWTManager:
    """Test JWT token management."""
    
    def test_create_access_token(self, app):
        """Test access token creation."""
        with app.app_context():
            token = JWTManager.create_access_token("user-123")
            assert token is not None
            assert isinstance(token, str)
    
    def test_decode_valid_token(self, app):
        """Test decoding valid token."""
        with app.app_context():
            token = JWTManager.create_access_token("user-123")
            payload = JWTManager.decode_token(token)
            assert payload is not None
            assert payload["sub"] == "user-123"
            assert payload["type"] == "access"
    
    def test_verify_access_token(self, app):
        """Test verifying access token."""
        with app.app_context():
            token = JWTManager.create_access_token("user-123")
            payload = JWTManager.verify_access_token(token)
            assert payload is not None
            assert payload["sub"] == "user-123"
    
    def test_verify_refresh_token(self, app):
        """Test verifying refresh token."""
        with app.app_context():
            token = JWTManager.create_refresh_token("user-123")
            payload = JWTManager.verify_refresh_token(token)
            assert payload is not None
            assert payload["type"] == "refresh"
    
    def test_invalid_token_returns_none(self, app):
        """Test invalid token returns None."""
        with app.app_context():
            payload = JWTManager.decode_token("invalid-token")
            assert payload is None
    
    def test_get_user_id_from_token(self, app):
        """Test extracting user ID from token."""
        with app.app_context():
            token = JWTManager.create_access_token("user-456")
            user_id = JWTManager.get_user_id_from_token(token)
            assert user_id == "user-456"


class TestRefreshTokenModel:
    """Test RefreshToken model."""
    
    def test_create_token(self, app):
        """Test creating a refresh token."""
        with app.app_context():
            user_id = "test-user-123"
            token, raw_token = RefreshToken.create_token(
                user_id=user_id,
                expires_delta=timedelta(days=7),
            )
            
            assert token is not None
            assert token.user_id == user_id
            assert token.is_valid() is True
            assert token.is_revoked is False
    
    def test_revoke_token(self, app):
        """Test revoking a token."""
        with app.app_context():
            token, _ = RefreshToken.create_token(
                user_id="test-user",
                expires_delta=timedelta(days=7),
            )
            
            token.revoke()
            assert token.is_valid() is False
            assert token.is_revoked is True
    
    def test_find_by_hash(self, app):
        """Test finding token by hash."""
        with app.app_context():
            token, raw_token = RefreshToken.create_token(
                user_id="test-user",
                expires_delta=timedelta(days=7),
            )
            
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            found = RefreshToken.find_by_hash(token_hash)
            
            assert found is not None
            assert found.id == token.id
    
    def test_token_rotation(self, app):
        """Test token rotation."""
        with app.app_context():
            old_token, _ = RefreshToken.create_token(
                user_id="test-user",
                expires_delta=timedelta(days=7),
            )
            
            new_token, raw_new = RefreshToken.create_rotation_token(
                old_token=old_token,
                expires_delta=timedelta(days=7),
            )
            
            assert old_token.is_used is True
            assert old_token.is_valid() is False
            assert new_token.is_valid() is True
            assert new_token.token_family == old_token.token_family


class TestLoginAttemptModel:
    """Test LoginAttempt model."""
    
    def test_record_attempt_success(self, app):
        """Test recording successful login."""
        with app.app_context():
            attempt = LoginAttempt.record_attempt(
                email="user@example.com",
                ip_address="127.0.0.1",
                successful=True,
            )
            
            assert attempt is not None
            assert attempt.successful is True
    
    def test_record_attempt_failure(self, app):
        """Test recording failed login."""
        with app.app_context():
            attempt = LoginAttempt.record_attempt(
                email="user@example.com",
                ip_address="127.0.0.1",
                successful=False,
                failure_reason="invalid_password",
            )
            
            assert attempt is not None
            assert attempt.successful is False
            assert attempt.failure_reason == "invalid_password"
    
    def test_get_failed_count(self, app):
        """Test getting failed attempt count."""
        with app.app_context():
            for _ in range(3):
                LoginAttempt.record_attempt(
                    email="user@example.com",
                    ip_address="127.0.0.1",
                    successful=False,
                )
            
            count = LoginAttempt.get_failed_count("user@example.com", minutes=60)
            assert count == 3


class TestOTPCodeModel:
    """Test OTPCode model."""
    
    def test_generate_otp(self, app):
        """Test OTP generation."""
        with app.app_context():
            otp, raw_code = OTPCode.generate_otp(
                user_id="test-user",
                code_type="email",
                purpose="verification",
            )
            
            assert otp is not None
            assert len(raw_code) == 6
            assert raw_code.isdigit()
    
    def test_verify_otp_correct(self, app):
        """Test verifying correct OTP."""
        with app.app_context():
            otp, raw_code = OTPCode.generate_otp(
                user_id="test-user",
                purpose="verification",
            )
            
            result = otp.verify(raw_code)
            assert result is True
            assert otp.is_verified is True
    
    def test_verify_otp_incorrect(self, app):
        """Test verifying incorrect OTP."""
        with app.app_context():
            otp, _ = OTPCode.generate_otp(
                user_id="test-user",
                purpose="verification",
            )
            
            result = otp.verify("000000")
            assert result is False
            assert otp.attempts == 1


class TestPasswordResetTokenModel:
    """Test PasswordResetToken model."""
    
    def test_generate_token(self, app):
        """Test password reset token generation."""
        with app.app_context():
            token, raw_token = PasswordResetToken.generate_token(
                user_id="test-user",
                expires_minutes=60,
            )
            
            assert token is not None
            assert len(raw_token) > 20
            assert token.is_used is False
            assert token.is_revoked is False
    
    def test_mark_used(self, app):
        """Test marking token as used."""
        with app.app_context():
            token, _ = PasswordResetToken.generate_token(user_id="test-user")
            token.mark_used(ip_address="127.0.0.1")
            
            assert token.is_used is True
            assert token.used_at is not None


class TestEmailVerificationModel:
    """Test EmailVerification model."""
    
    def test_generate_token(self, app):
        """Test email verification token generation."""
        with app.app_context():
            token, raw_token = EmailVerification.generate_token(
                user_id="test-user",
                email="user@example.com",
            )
            
            assert token is not None
            assert token.email == "user@example.com"
            assert token.is_verified is False
    
    def test_verify(self, app):
        """Test email verification."""
        with app.app_context():
            token, _ = EmailVerification.generate_token(
                user_id="test-user",
                email="user@example.com",
            )
            
            token.verify(ip_address="127.0.0.1")
            assert token.is_verified is True
            assert token.verified_at is not None


class TestUserSessionModel:
    """Test UserSession model."""
    
    def test_create_session(self, app):
        """Test session creation."""
        with app.app_context():
            session, raw_token = UserSession.create_session(
                user_id="test-user",
                remember=True,
                user_agent="Mozilla/5.0",
            )
            
            assert session is not None
            assert session.is_remember is True
            assert session.device_type == "Desktop"
            assert session.browser == "Unknown"
    
    def test_revoke_session(self, app):
        """Test session revocation."""
        with app.app_context():
            session, _ = UserSession.create_session(user_id="test-user")
            session.revoke()
            
            assert session.is_active is False
    
    def test_find_valid_session(self, app):
        """Test finding valid session."""
        with app.app_context():
            session, raw_token = UserSession.create_session(user_id="test-user")
            
            found = UserSession.find_valid_by_token(raw_token)
            assert found is not None
            assert found.id == session.id


class TestAuthService:
    """Test AuthService."""
    
    def test_register_creates_user(self, app):
        """Test user registration."""
        with app.app_context():
            result = AuthService.register(
                email="newuser@example.com",
                password="StrongPass123!",
                first_name="New",
                last_name="User",
            )
            
            assert result.success is True
            assert result.user is not None
            assert result.user.email == "newuser@example.com"
            assert result.requires_verification is True
    
    def test_register_duplicate_email_fails(self, app, test_user):
        """Test duplicate email registration fails."""
        with app.app_context():
            with pytest.raises(AuthError) as exc_info:
                AuthService.register(
                    email="test@example.com",
                    password="StrongPass123!",
                )
            
            assert exc_info.value.code == "email_exists"
    
    def test_login_success(self, app, test_user):
        """Test successful login."""
        from models.user import User
        from app import db
        with app.app_context():
            result = AuthService.login(
                email="test@example.com",
                password="TestPassword123!",
            )
            
            assert result.success is True
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.session_token is not None
    
    def test_login_invalid_email(self, app):
        """Test login with invalid email."""
        with app.app_context():
            with pytest.raises(InvalidCredentialsError):
                AuthService.login(
                    email="wrong@example.com",
                    password="anypassword",
                )
    
    def test_login_invalid_password(self, app, test_user):
        """Test login with invalid password."""
        with app.app_context():
            with pytest.raises(InvalidCredentialsError):
                AuthService.login(
                    email="test@example.com",
                    password="WrongPassword123!",
                )
    
    def test_logout(self, app, test_user):
        """Test logout."""
        with app.app_context():
            login_result = AuthService.login(
                email="test@example.com",
                password="TestPassword123!",
            )
            
            logout_result = AuthService.logout(
                user_id=test_user,
                all_sessions=True,
            )
            
            assert logout_result is True
    
    def test_request_password_reset(self, app, test_user):
        """Test password reset request."""
        with app.app_context():
            result = AuthService.request_password_reset(
                email="test@example.com",
            )
            
            assert result is True
    
    def test_reset_password(self, app, test_user):
        """Test password reset."""
        with app.app_context():
            reset_token, raw_token = PasswordResetToken.generate_token(
                user_id=test_user,
            )
            
            result = AuthService.reset_password(
                token=raw_token,
                new_password="NewStrongPass456!",
            )
            
            assert result is True
            
            login_result = AuthService.login(
                email="test@example.com",
                password="NewStrongPass456!",
            )
            
            assert login_result.success is True


class TestAuthErrors:
    """Test authentication error handling."""
    
    def test_auth_error_properties(self):
        """Test AuthError properties."""
        error = AuthError("Test error", code="test_code", status_code=400)
        
        assert error.message == "Test error"
        assert error.code == "test_code"
        assert error.status_code == 400
    
    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError."""
        error = InvalidCredentialsError()
        
        assert error.code == "invalid_credentials"
        assert error.status_code == 401
    
    def test_account_locked_error(self):
        """Test AccountLockedError."""
        error = AccountLockedError(retry_after=300)
        
        assert error.code == "account_locked"
        assert error.status_code == 423
        assert error.retry_after == 300


class TestAuthRoutes:
    """Test authentication routes."""
    
    def test_login_page_get(self, client):
        """Test login page GET request."""
        response = client.get("/auth/login")
        assert response.status_code == 200
    
    def test_register_page_get(self, client):
        """Test register page GET request."""
        response = client.get("/auth/register")
        assert response.status_code == 200
    
    def test_forgot_password_page_get(self, client):
        """Test forgot password page GET request."""
        response = client.get("/auth/forgot-password")
        assert response.status_code == 200
    
    def test_csrf_token_endpoint(self, client):
        """Test CSRF token endpoint."""
        response = client.get("/auth/csrf-token")
        assert response.status_code == 200
        data = response.get_json()
        assert "csrf_token" in data


class TestAuditLog:
    """Test AuditLog model."""
    
    def test_log_action(self, app):
        """Test logging an action."""
        with app.app_context():
            log = AuditLog.log(
                action="user_login",
                category=AuditLog.CATEGORY_AUTH,
                user_id="test-user",
                ip_address="127.0.0.1",
            )
            
            assert log is not None
            assert log.action == "user_login"
            assert log.category == AuditLog.CATEGORY_AUTH
    
    def test_log_with_values(self, app):
        """Test logging with old/new values."""
        with app.app_context():
            log = AuditLog.log(
                action="password_changed",
                category=AuditLog.CATEGORY_ACCOUNT,
                user_id="test-user",
                old_values={"password_changed": False},
                new_values={"password_changed": True},
            )
            
            assert log.old_values is not None
            assert log.new_values is not None
    
    def test_to_dict(self, app):
        """Test audit log to dict conversion."""
        with app.app_context():
            log = AuditLog.log(
                action="test_action",
                category=AuditLog.CATEGORY_AUTH,
            )
            
            log_dict = log.to_dict()
            assert "id" in log_dict
            assert "action" in log_dict
            assert "category" in log_dict


class TestSecurityFeatures:
    """Test security features."""
    
    def test_password_hashing(self, app):
        """Test password hashing."""
        with app.app_context():
            user = User(
                email="secure@example.com",
            )
            user.set_password("MySecurePassword123!")
            
            db.session.add(user)
            db.session.commit()
            
            assert user.password_hash is not None
            assert user.verify_password("MySecurePassword123!") is True
            assert user.verify_password("WrongPassword") is False
    
    def test_audit_log_on_login(self, app, test_user):
        """Test audit log is created on login."""
        with app.app_context():
            AuthService.login(
                email="test@example.com",
                password="TestPassword123!",
                ip_address="127.0.0.1",
            )
            
            logs = AuditLog.query.filter_by(
                action="user_login",
                user_id=test_user,
            ).all()
            
            assert len(logs) >= 1
            assert logs[0].ip_address == "127.0.0.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])