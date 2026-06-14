"""Settings routes."""

from flask import Blueprint, request, jsonify, render_template

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/")
def index():
    """Settings home page."""
    return render_template("settings/index.html")


@settings_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """Profile settings page."""
    return render_template("settings/profile.html")


@settings_bp.route("/security", methods=["GET", "POST"])
def security():
    """Security settings page."""
    return render_template("settings/security.html")


@settings_bp.route("/notifications", methods=["GET", "POST"])
def notifications():
    """Notification settings page."""
    return render_template("settings/notifications.html")


@settings_bp.route("/team")
def team():
    """Team settings page."""
    return render_template("settings/team.html")


@settings_bp.route("/integrations")
def integrations():
    """Integrations settings page."""
    return render_template("settings/integrations.html")


@settings_bp.route("/api/settings", methods=["GET", "PUT"])
def api_settings():
    """Settings API."""
    return jsonify({"message": "Settings API"})


@settings_bp.route("/api/profile", methods=["GET", "PUT"])
def api_profile():
    """Profile settings API."""
    return jsonify({"message": "Profile API"})


@settings_bp.route("/api/password", methods=["PUT"])
def api_password():
    """Password change API."""
    return jsonify({"message": "Password API"})


@settings_bp.route("/api/2fa", methods=["GET", "POST", "DELETE"])
def api_2fa():
    """Two-factor authentication API."""
    return jsonify({"message": "2FA API"})


@settings_bp.route("/api/notifications", methods=["GET", "PUT"])
def api_notifications():
    """Notification settings API."""
    return jsonify({"message": "Notifications API"})


@settings_bp.route("/api/api-keys", methods=["GET", "POST"])
def api_keys():
    """API keys API."""
    return jsonify({"message": "API keys API"})


@settings_bp.route("/api/api-keys/<key_id>", methods=["DELETE"])
def api_delete_key(key_id):
    """Delete API key API."""
    return jsonify({"message": "Delete key API"})