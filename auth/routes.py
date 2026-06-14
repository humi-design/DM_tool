"""Authentication routes."""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, g
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    
    if request.method == "POST":
        pass
    
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    
    if request.method == "POST":
        pass
    
    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """User logout."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Forgot password page."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password page."""
    return render_template("auth/reset_password.html")


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    """Verify email address."""
    return render_template("auth/verify_email.html")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    """Verify OTP code."""
    return render_template("auth/verify_otp.html")


@auth_bp.route("/oauth/google")
def google_oauth():
    """Initiate Google OAuth flow."""
    return redirect(url_for("auth.google_callback"))


@auth_bp.route("/oauth/google/callback")
def google_callback():
    """Google OAuth callback."""
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """API endpoint for login."""
    return jsonify({"message": "Login endpoint"})


@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    """API endpoint for registration."""
    return jsonify({"message": "Register endpoint"})


@auth_bp.route("/api/logout", methods=["POST"])
def api_logout():
    """API endpoint for logout."""
    return jsonify({"message": "Logout endpoint"})


@auth_bp.route("/api/refresh", methods=["POST"])
def api_refresh():
    """API endpoint for token refresh."""
    return jsonify({"message": "Refresh endpoint"})


@auth_bp.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    """API endpoint for forgot password."""
    return jsonify({"message": "Forgot password endpoint"})


@auth_bp.route("/api/reset-password", methods=["POST"])
def api_reset_password():
    """API endpoint for reset password."""
    return jsonify({"message": "Reset password endpoint"})


@auth_bp.route("/api/verify-email", methods=["POST"])
def api_verify_email():
    """API endpoint for email verification."""
    return jsonify({"message": "Verify email endpoint"})


@auth_bp.route("/api/verify-otp", methods=["POST"])
def api_verify_otp():
    """API endpoint for OTP verification."""
    return jsonify({"message": "Verify OTP endpoint"})


@auth_bp.route("/api/resend-otp", methods=["POST"])
def api_resend_otp():
    """API endpoint for resending OTP."""
    return jsonify({"message": "Resend OTP endpoint"})


@auth_bp.route("/csrf-token")
def csrf_token():
    """Get CSRF token for forms."""
    return jsonify({"csrf_token": generate_csrf()})