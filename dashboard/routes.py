"""Dashboard routes."""

from flask import Blueprint, request, jsonify, render_template, g
from flask_login import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    """Dashboard home page."""
    return render_template("dashboard/index.html")


@dashboard_bp.route("/overview")
@login_required
def overview():
    """Dashboard overview page."""
    return render_template("dashboard/overview.html")


@dashboard_bp.route("/activity")
@login_required
def activity():
    """Recent activity page."""
    return render_template("dashboard/activity.html")


@dashboard_bp.route("/quick-actions")
@login_required
def quick_actions():
    """Quick actions page."""
    return render_template("dashboard/quick_actions.html")


@dashboard_bp.route("/api/stats", methods=["GET"])
@login_required
def api_stats():
    """Dashboard stats API."""
    return jsonify({"message": "Stats API"})


@dashboard_bp.route("/api/activity", methods=["GET"])
@login_required
def api_activity():
    """Activity feed API."""
    return jsonify({"message": "Activity API"})


@dashboard_bp.route("/api/notifications", methods=["GET"])
@login_required
def api_notifications():
    """Notifications API."""
    return jsonify({"message": "Notifications API"})


@dashboard_bp.route("/api/notifications/<notification_id>/read", methods=["POST"])
@login_required
def api_mark_read(notification_id):
    """Mark notification as read API."""
    return jsonify({"message": "Mark read API"})