"""Users routes."""

from flask import Blueprint, request, jsonify, render_template

users_bp = Blueprint("users", __name__)


@users_bp.route("/")
def index():
    """Users list page."""
    return render_template("users/index.html")


@users_bp.route("/<user_id>")
def detail(user_id):
    """User detail page."""
    return render_template("users/detail.html", user_id=user_id)


@users_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """User profile page."""
    return render_template("users/profile.html")


@users_bp.route("/settings", methods=["GET", "POST"])
def user_settings():
    """User settings page."""
    return render_template("users/settings.html")


@users_bp.route("/api/me", methods=["GET"])
def api_me():
    """Get current user."""
    return jsonify({"message": "Current user endpoint"})


@users_bp.route("/api/users", methods=["GET"])
def api_list():
    """List users API."""
    return jsonify({"message": "List users endpoint"})


@users_bp.route("/api/users/<user_id>", methods=["GET", "PUT", "DELETE"])
def api_detail(user_id):
    """User detail API."""
    return jsonify({"message": "User detail endpoint"})


@users_bp.route("/api/profile", methods=["GET", "PUT"])
def api_profile():
    """Profile API."""
    return jsonify({"message": "Profile endpoint"})