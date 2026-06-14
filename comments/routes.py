"""Comments routes."""

from flask import Blueprint, request, jsonify, render_template

comments_bp = Blueprint("comments", __name__)


@comments_bp.route("/")
def index():
    """Comments list page."""
    return render_template("comments/index.html")


@comments_bp.route("/<comment_id>")
def detail(comment_id):
    """Comment detail page."""
    return render_template("comments/detail.html", comment_id=comment_id)


@comments_bp.route("/auto-reply", methods=["GET", "POST"])
def auto_reply():
    """Auto reply configuration page."""
    return render_template("comments/auto_reply.html")


@comments_bp.route("/filters", methods=["GET", "POST"])
def filters():
    """Comment filters page."""
    return render_template("comments/filters.html")


@comments_bp.route("/api/comments", methods=["GET"])
def api_list():
    """Comments API."""
    return jsonify({"message": "Comments API"})


@comments_bp.route("/api/comments/<comment_id>", methods=["GET", "PUT", "DELETE"])
def api_detail(comment_id):
    """Comment detail API."""
    return jsonify({"message": "Comment detail API"})


@comments_bp.route("/api/comments/<comment_id>/reply", methods=["POST"])
def api_reply(comment_id):
    """Reply to comment API."""
    return jsonify({"message": "Reply API"})


@comments_bp.route("/api/comments/<comment_id>/hide", methods=["POST"])
def api_hide(comment_id):
    """Hide comment API."""
    return jsonify({"message": "Hide API"})


@comments_bp.route("/api/comments/<comment_id>/spam", methods=["POST"])
def api_spam(comment_id):
    """Mark as spam API."""
    return jsonify({"message": "Spam API"})


@comments_bp.route("/api/auto-reply", methods=["GET", "POST", "PUT"])
def api_auto_reply():
    """Auto reply configuration API."""
    return jsonify({"message": "Auto reply API"})


@comments_bp.route("/api/filters", methods=["GET", "POST", "PUT"])
def api_filters():
    """Comment filters API."""
    return jsonify({"message": "Filters API"})