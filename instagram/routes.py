"""Instagram routes."""

from flask import Blueprint, request, jsonify, render_template

instagram_bp = Blueprint("instagram", __name__)


@instagram_bp.route("/accounts")
def accounts():
    """Instagram accounts list page."""
    return render_template("instagram/accounts.html")


@instagram_bp.route("/accounts/<account_id>")
def account_detail(account_id):
    """Instagram account detail page."""
    return render_template("instagram/account_detail.html", account_id=account_id)


@instagram_bp.route("/accounts/<account_id>/connect", methods=["GET", "POST"])
def connect_account(account_id):
    """Connect Instagram account."""
    return render_template("instagram/connect.html", account_id=account_id)


@instagram_bp.route("/posts")
def posts():
    """Instagram posts list page."""
    return render_template("instagram/posts.html")


@instagram_bp.route("/posts/<post_id>")
def post_detail(post_id):
    """Instagram post detail page."""
    return render_template("instagram/post_detail.html", post_id=post_id)


@instagram_bp.route("/schedule", methods=["GET", "POST"])
def schedule():
    """Schedule post page."""
    return render_template("instagram/schedule.html")


@instagram_bp.route("/api/accounts", methods=["GET", "POST"])
def api_accounts():
    """Instagram accounts API."""
    return jsonify({"message": "Accounts API"})


@instagram_bp.route("/api/accounts/<account_id>", methods=["GET", "PUT", "DELETE"])
def api_account_detail(account_id):
    """Instagram account detail API."""
    return jsonify({"message": "Account detail API"})


@instagram_bp.route("/api/accounts/<account_id>/sync", methods=["POST"])
def api_sync(account_id):
    """Sync Instagram account."""
    return jsonify({"message": "Sync endpoint"})


@instagram_bp.route("/api/posts", methods=["GET"])
def api_posts():
    """Instagram posts API."""
    return jsonify({"message": "Posts API"})


@instagram_bp.route("/api/posts/<post_id>", methods=["GET", "PUT"])
def api_post_detail(post_id):
    """Instagram post detail API."""
    return jsonify({"message": "Post detail API"})


@instagram_bp.route("/api/posts/<post_id>/analytics", methods=["GET"])
def api_post_analytics(post_id):
    """Instagram post analytics API."""
    return jsonify({"message": "Post analytics API"})