"""Users routes."""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from functools import wraps

from app import db
from models.user import User
from utils.jwt import jwt_required, get_current_user_id

users_bp = Blueprint("users", __name__)


def api_response(f):
    """Decorator for consistent API responses."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                return jsonify(result[0]), result[1] if len(result) > 1 else 200
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e), "success": False}), 500
    return wrapper


@users_bp.route("/")
@login_required
def index():
    """Users list page."""
    return render_template("users/index.html")


@users_bp.route("/<user_id>")
@login_required
def detail(user_id):
    """User detail page."""
    return render_template("users/detail.html", user_id=user_id)


@users_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile page."""
    return render_template("users/profile.html")


@users_bp.route("/settings", methods=["GET", "POST"])
@login_required
def user_settings():
    """User settings page."""
    return render_template("users/settings.html")


@users_bp.route("/api/me", methods=["GET"])
@jwt_required
@api_response
def api_me():
    """Get current user."""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    if not user:
        return {"success": False, "error": "User not found"}, 404
    return {"success": True, "data": user.to_dict()}


@users_bp.route("/api/profile", methods=["GET", "PUT"])
@jwt_required
@api_response
def api_profile():
    """Get or update current user profile."""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    if not user:
        return {"success": False, "error": "User not found"}, 404
    
    if request.method == "GET":
        return {"success": True, "data": user.to_dict()}
    
    # PUT - Update profile
    data = request.get_json()
    if not data:
        return {"success": False, "error": "No data provided"}, 400
    
    # Update allowed fields
    for field in ["first_name", "last_name", "phone", "locale", "timezone"]:
        if field in data:
            setattr(user, field, data[field])
    
    # Handle settings update
    if "settings" in data:
        user.settings.update(data["settings"])
    
    db.session.commit()
    return {"success": True, "data": user.to_dict()}


@users_bp.route("/api/profile/avatar", methods=["POST"])
@jwt_required
@api_response
def api_update_avatar():
    """Update user avatar."""
    user_id = get_current_user_id()
    user = User.query.get(user_id)
    if not user:
        return {"success": False, "error": "User not found"}, 404
    
    data = request.get_json()
    if not data or "avatar_url" not in data:
        return {"success": False, "error": "Avatar URL required"}, 400
    
    user.avatar_url = data["avatar_url"]
    db.session.commit()
    return {"success": True, "data": user.to_dict()}