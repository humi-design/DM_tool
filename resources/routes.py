"""Resources routes."""

from flask import Blueprint, request, jsonify, render_template

resources_bp = Blueprint("resources", __name__)


@resources_bp.route("/")
def index():
    """Resources list page."""
    return render_template("resources/index.html")


@resources_bp.route("/<resource_id>")
def detail(resource_id):
    """Resource detail page."""
    return render_template("resources/detail.html", resource_id=resource_id)


@resources_bp.route("/upload", methods=["GET", "POST"])
def upload():
    """Upload resource page."""
    return render_template("resources/upload.html")


@resources_bp.route("/api/resources", methods=["GET", "POST"])
def api_list():
    """Resources API."""
    return jsonify({"message": "Resources API"})


@resources_bp.route("/api/resources/<resource_id>", methods=["GET", "PUT", "DELETE"])
def api_detail(resource_id):
    """Resource detail API."""
    return jsonify({"message": "Resource detail API"})


@resources_bp.route("/api/resources/upload", methods=["POST"])
def api_upload():
    """Upload resource API."""
    return jsonify({"message": "Upload API"})