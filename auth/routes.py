"""Authentication routes."""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, g, make_response
from flask_wtf.csrf import generate_csrf

from services.auth_service import (
    AuthService,
    AuthError,
    InvalidCredentialsError,
    RateLimitError,
    AccountLockedError,
    GoogleOAuthService,
)
from utils.jwt import jwt_required, get_client_ip, get_user_agent, get_device_fingerprint
from utils.validators import (
    validate_email,
    validate_password,
    validate_password_confirmation,
    validate_name,
    validate_otp_code,
    ValidationResult,
)
from models.auth import UserSession
from models.audit_log import AuditLog
from auth.rate_limiting import (
    login_limiter,
    register_limiter,
    otp_request_limiter,
    password_reset_limiter,
)

auth_bp = Blueprint("auth", __name__)


def _get_request_info():
    """Get request information for logging."""
    return {
        "ip_address": get_client_ip(),
        "user_agent": get_user_agent(),
        "device_fingerprint": get_device_fingerprint(),
    }


def _handle_auth_error(error: AuthError):
    """Convert AuthError to JSON response."""
    response = {
        "success": False,
        "error": {
            "code": error.code,
            "message": error.message,
        }
    }
    if isinstance(error, AccountLockedError):
        response["error"]["retry_after"] = error.retry_after
    return jsonify(response), error.status_code


# ==================== HTML Routes ====================

@auth_bp.route("/login", methods=["GET", "POST"])
@login_limiter
def login():
    """User login page."""
    if request.method == "GET":
        return render_template("auth/login.html")
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        email = data.get("email", "").strip()
        password = data.get("password", "")
        remember = data.get("remember", False)
        
        result = AuthService.login(
            email=email,
            password=password,
            remember=remember,
            **_get_request_info(),
        )
        
        response = make_response(jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "id": result.user.id,
                "email": result.user.email,
                "full_name": result.user.full_name,
            },
        }))
        
        response.set_cookie(
            "access_token",
            result.access_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 15,
        )
        response.set_cookie(
            "refresh_token",
            result.refresh_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,
        )
        response.set_cookie(
            "session_token",
            result.session_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 60 * 24 * (30 if remember else 7),
        )
        
        return response
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/register", methods=["GET", "POST"])
@register_limiter
def register():
    """User registration page."""
    if request.method == "GET":
        return render_template("auth/register.html")
    
    try:
        data = request.get_json() if request.is_json else request.form
        
        email = data.get("email", "").strip()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        
        email_validation = validate_email(email)
        if not email_validation.is_valid:
            raise AuthError(email_validation.error, code="invalid_email")
        
        password_validation = validate_password(password)
        if not password_validation.is_valid:
            error = password_validation.errors[0] if password_validation.errors else "Invalid password"
            raise AuthError(error, code="invalid_password")
        
        confirm_validation = validate_password_confirmation(password, confirm_password)
        if not confirm_validation.is_valid:
            raise AuthError(confirm_validation.error, code="password_mismatch")
        
        if first_name:
            name_validation = validate_name(first_name, "First name")
            if not name_validation.is_valid:
                raise AuthError(name_validation.error, code="invalid_first_name")
        
        if last_name:
            name_validation = validate_name(last_name, "Last name")
            if not name_validation.is_valid:
                raise AuthError(name_validation.error, code="invalid_last_name")
        
        result = AuthService.register(
            email=email,
            password=password,
            first_name=first_name or None,
            last_name=last_name or None,
            **_get_request_info(),
        )
        
        return jsonify({
            "success": True,
            "message": result.message,
            "requires_verification": result.requires_verification,
        }), 201
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    """User logout."""
    try:
        session_id = getattr(g, "current_session", None)
        session_id = session_id.id if session_id else None
        
        AuthService.logout(
            user_id=g.current_user_id,
            session_id=session_id,
            all_sessions=request.args.get("all", "false").lower() == "true",
            **_get_request_info(),
        )
        
        response = make_response(jsonify({
            "success": True,
            "message": "Logged out successfully",
        }))
        
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.delete_cookie("session_token")
        
        return response
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@password_reset_limiter
def forgot_password():
    """Forgot password page."""
    if request.method == "GET":
        return render_template("auth/forgot_password.html")
    
    try:
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip()
        
        email_validation = validate_email(email)
        if not email_validation.is_valid:
            raise AuthError(email_validation.error, code="invalid_email")
        
        AuthService.request_password_reset(email, **_get_request_info())
        
        return jsonify({
            "success": True,
            "message": "If an account with that email exists, we've sent password reset instructions.",
        })
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password page."""
    if request.method == "GET":
        return render_template("auth/reset_password.html", token=token)
    
    try:
        data = request.get_json() if request.is_json else request.form
        new_password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")
        
        password_validation = validate_password(new_password)
        if not password_validation.is_valid:
            error = password_validation.errors[0] if password_validation.errors else "Invalid password"
            raise AuthError(error, code="invalid_password")
        
        confirm_validation = validate_password_confirmation(new_password, confirm_password)
        if not confirm_validation.is_valid:
            raise AuthError(confirm_validation.error, code="password_mismatch")
        
        AuthService.reset_password(token, new_password, **_get_request_info())
        
        response = make_response(jsonify({
            "success": True,
            "message": "Password has been reset successfully.",
        }))
        
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.delete_cookie("session_token")
        
        return response
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    """Verify email address."""
    try:
        AuthService.verify_email(token, **_get_request_info())
        
        return render_template("auth/email_verified.html", success=True)
        
    except AuthError as e:
        return render_template("auth/email_verified.html", success=False, message=e.message)


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    """Verify OTP code."""
    if request.method == "GET":
        return render_template("auth/verify_otp.html")
    
    try:
        data = request.get_json() if request.is_json else request.form
        user_id = data.get("user_id", "").strip()
        code = data.get("code", "").strip()
        
        otp_validation = validate_otp_code(code)
        if not otp_validation.is_valid:
            raise AuthError(otp_validation.error, code="invalid_otp")
        
        result = AuthService.verify_otp(user_id, code, **_get_request_info())
        
        response = make_response(jsonify({
            "success": True,
            "message": "Verification successful",
            "user": {
                "id": result.user.id,
                "email": result.user.email,
            },
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
        }))
        
        response.set_cookie(
            "access_token",
            result.access_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 15,
        )
        response.set_cookie(
            "refresh_token",
            result.refresh_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,
        )
        
        return response
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    """Resend email verification."""
    try:
        data = request.get_json() if request.is_json else request.form
        email = data.get("email", "").strip()
        
        email_validation = validate_email(email)
        if not email_validation.is_valid:
            raise AuthError(email_validation.error, code="invalid_email")
        
        AuthService.resend_verification(email, **_get_request_info())
        
        return jsonify({
            "success": True,
            "message": "Verification email sent if account exists.",
        })
        
    except AuthError as e:
        return _handle_auth_error(e)


# ==================== OAuth Routes ====================

@auth_bp.route("/oauth/google")
def google_oauth():
    """Initiate Google OAuth flow."""
    redirect_uri = url_for("auth.google_callback", _external=True, _scheme="https" if request.is_secure else "http")
    auth_url = GoogleOAuthService.get_authorization_url(redirect_uri)
    return redirect(auth_url)


@auth_bp.route("/oauth/google/callback")
def google_callback():
    """Google OAuth callback."""
    try:
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")
        
        if error:
            raise AuthError(f"Google OAuth error: {error}", code="oauth_error")
        
        if not code:
            raise AuthError("Missing authorization code", code="oauth_error")
        
        redirect_uri = url_for("auth.google_callback", _external=True, _scheme="https" if request.is_secure else "http")
        tokens = GoogleOAuthService.exchange_code_for_tokens(code, redirect_uri)
        google_user = GoogleOAuthService.get_user_info(tokens.get("access_token"))
        
        result = GoogleOAuthService.authenticate_or_register(google_user, **_get_request_info())
        
        response = make_response(redirect(url_for("dashboard.index")))
        
        response.set_cookie(
            "access_token",
            result.access_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 15,
        )
        response.set_cookie(
            "refresh_token",
            result.refresh_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,
        )
        
        return response
        
    except AuthError as e:
        return render_template("auth/oauth_error.html", message=e.message)


# ==================== API Routes ====================

@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """API endpoint for login."""
    return login()


@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    """API endpoint for registration."""
    return register()


@auth_bp.route("/api/logout", methods=["POST"])
def api_logout():
    """API endpoint for logout."""
    return logout()


@auth_bp.route("/api/refresh", methods=["POST"])
def api_refresh():
    """API endpoint for token refresh."""
    try:
        refresh_token = request.cookies.get("refresh_token") or request.json.get("refresh_token") if request.is_json else request.cookies.get("refresh_token")
        
        if not refresh_token:
            raise AuthError("Refresh token required", code="missing_token", status_code=401)
        
        result = AuthService.refresh_tokens(refresh_token, **_get_request_info())
        
        response = make_response(jsonify({
            "success": True,
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
        }))
        
        response.set_cookie(
            "access_token",
            result.access_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 15,
        )
        response.set_cookie(
            "refresh_token",
            result.refresh_token,
            httponly=True,
            secure=request.is_secure,
            samesite="Lax",
            max_age=60 * 60 * 24 * 30,
        )
        
        return response
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    """API endpoint for forgot password."""
    return forgot_password()


@auth_bp.route("/api/reset-password", methods=["POST"])
def api_reset_password():
    """API endpoint for reset password."""
    token = request.json.get("token") if request.is_json else request.form.get("token")
    if not token:
        return jsonify({"success": False, "error": {"code": "missing_token", "message": "Token required"}}), 400
    return reset_password(token)


@auth_bp.route("/api/verify-email", methods=["POST"])
def api_verify_email():
    """API endpoint for email verification."""
    token = request.json.get("token") if request.is_json else request.form.get("token")
    if not token:
        return jsonify({"success": False, "error": {"code": "missing_token", "message": "Token required"}}), 400
    return verify_email(token)


@auth_bp.route("/api/verify-otp", methods=["POST"])
def api_verify_otp():
    """API endpoint for OTP verification."""
    return verify_otp()


@auth_bp.route("/api/resend-otp", methods=["POST"])
def api_resend_otp():
    """API endpoint for resending OTP."""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        code_type = data.get("type", "email")
        
        if not user_id:
            raise AuthError("User ID required", code="missing_user_id")
        
        if code_type == "sms":
            phone = data.get("phone")
            if not phone:
                raise AuthError("Phone number required", code="missing_phone")
            AuthService.request_sms_otp(user_id, phone, **_get_request_info())
        else:
            raw_code = AuthService.request_email_otp(user_id, **_get_request_info())
        
        return jsonify({
            "success": True,
            "message": f"OTP sent via {code_type}",
        })
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/api/sessions", methods=["GET"])
@jwt_required
def api_sessions():
    """Get user sessions."""
    try:
        sessions = AuthService.get_user_sessions(g.current_user_id)
        
        return jsonify({
            "success": True,
            "sessions": [
                {
                    "id": s.id,
                    "device_type": s.device_type,
                    "browser": s.browser,
                    "os": s.os,
                    "ip_address": s.ip_address,
                    "location": s.location,
                    "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
                    "created_at": s.created_at.isoformat(),
                    "is_current": s.id == getattr(g, "current_session", None),
                }
                for s in sessions
            ],
        })
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/api/sessions/<session_id>", methods=["DELETE"])
@jwt_required
def api_revoke_session(session_id):
    """Revoke a specific session."""
    try:
        success = AuthService.revoke_session(g.current_user_id, session_id)
        
        if success:
            return jsonify({"success": True, "message": "Session revoked"})
        else:
            raise AuthError("Session not found", code="session_not_found", status_code=404)
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/api/sessions/revoke-all", methods=["POST"])
@jwt_required
def api_revoke_all_sessions():
    """Revoke all sessions except current."""
    try:
        current_session_id = getattr(g, "current_session", None)
        current_session_id = current_session_id.id if current_session_id else None
        
        count = UserSession.revoke_all_user_sessions(g.current_user_id, exclude_session_id=current_session_id)
        
        AuditLog.log(
            action="all_sessions_revoked",
            category=AuditLog.CATEGORY_AUTH,
            user_id=g.current_user_id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
        )
        
        return jsonify({
            "success": True,
            "message": f"Revoked {count} sessions",
        })
        
    except AuthError as e:
        return _handle_auth_error(e)


@auth_bp.route("/csrf-token", methods=["GET"])
def csrf_token():
    """Get CSRF token for forms."""
    return jsonify({
        "csrf_token": generate_csrf(),
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    """Get current authenticated user."""
    from models.user import User
    user = User.query.get(g.current_user_id)
    
    if not user:
        return jsonify({"success": False, "error": {"code": "user_not_found", "message": "User not found"}}), 404
    
    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    })