"""DM routes."""

from flask import Blueprint, request, jsonify, render_template

dm_bp = Blueprint("dm", __name__)


@dm_bp.route("/")
def index():
    """DM inbox page."""
    return render_template("dm/index.html")


@dm_bp.route("/threads")
def threads():
    """DM threads list page."""
    return render_template("dm/threads.html")


@dm_bp.route("/threads/<thread_id>")
def thread_detail(thread_id):
    """DM thread detail page."""
    return render_template("dm/thread_detail.html", thread_id=thread_id)


@dm_bp.route("/compose", methods=["GET", "POST"])
def compose():
    """Compose new DM page."""
    return render_template("dm/compose.html")


@dm_bp.route("/templates", methods=["GET", "POST"])
def templates():
    """DM templates page."""
    return render_template("dm/templates.html")


@dm_bp.route("/auto-reply", methods=["GET", "POST"])
def auto_reply():
    """Auto reply configuration page."""
    return render_template("dm/auto_reply.html")


@dm_bp.route("/api/threads", methods=["GET"])
def api_threads():
    """DM threads API."""
    return jsonify({"message": "Threads API"})


@dm_bp.route("/api/threads/<thread_id>", methods=["GET", "PUT"])
def api_thread_detail(thread_id):
    """DM thread detail API."""
    return jsonify({"message": "Thread detail API"})


@dm_bp.route("/api/threads/<thread_id>/messages", methods=["GET"])
def api_messages(thread_id):
    """DM messages API."""
    return jsonify({"message": "Messages API"})


@dm_bp.route("/api/threads/<thread_id>/send", methods=["POST"])
def api_send(thread_id):
    """Send DM API."""
    return jsonify({"message": "Send API"})


@dm_bp.route("/api/compose", methods=["POST"])
def api_compose():
    """Compose and send DM API."""
    return jsonify({"message": "Compose API"})


@dm_bp.route("/api/templates", methods=["GET", "POST"])
def api_templates():
    """DM templates API."""
    return jsonify({"message": "Templates API"})


@dm_bp.route("/api/templates/<template_id>", methods=["GET", "PUT", "DELETE"])
def api_template_detail(template_id):
    """DM template detail API."""
    return jsonify({"message": "Template detail API"})


@dm_bp.route("/api/auto-reply", methods=["GET", "POST", "PUT"])
def api_auto_reply():
    """Auto reply configuration API."""
    return jsonify({"message": "Auto reply API"})


@dm_bp.route("/api/mark-read/<thread_id>", methods=["POST"])
def api_mark_read(thread_id):
    """Mark thread as read API."""
    return jsonify({"message": "Mark read API"})


@dm_bp.route("/api/archive/<thread_id>", methods=["POST"])
def api_archive(thread_id):
    """Archive thread API."""
    return jsonify({"message": "Archive API"})


@dm_bp.route("/api/spam/<thread_id>", methods=["POST"])
def api_spam(thread_id):
    """Mark thread as spam API."""
    return jsonify({"message": "Spam API"})