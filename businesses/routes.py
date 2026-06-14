"""Businesses routes."""

from flask import Blueprint, request, jsonify, render_template

businesses_bp = Blueprint("businesses", __name__)


@businesses_bp.route("/")
def index():
    """Businesses list page."""
    return render_template("businesses/index.html")


@businesses_bp.route("/<business_id>")
def detail(business_id):
    """Business detail page."""
    return render_template("businesses/detail.html", business_id=business_id)


@businesses_bp.route("/create", methods=["GET", "POST"])
def create():
    """Create business page."""
    return render_template("businesses/create.html")


@businesses_bp.route("/<business_id>/edit", methods=["GET", "POST"])
def edit(business_id):
    """Edit business page."""
    return render_template("businesses/edit.html", business_id=business_id)


@businesses_bp.route("/<business_id>/profiles")
def profiles(business_id):
    """Business profiles page."""
    return render_template("businesses/profiles.html", business_id=business_id)


@businesses_bp.route("/<business_id>/connect/<platform>", methods=["GET", "POST"])
def connect(business_id, platform):
    """Connect social media platform."""
    return render_template("businesses/connect.html", business_id=business_id, platform=platform)


@businesses_bp.route("/api/businesses", methods=["GET", "POST"])
def api_list():
    """Businesses API."""
    return jsonify({"message": "Businesses API"})


@businesses_bp.route("/api/businesses/<business_id>", methods=["GET", "PUT", "DELETE"])
def api_detail(business_id):
    """Business detail API."""
    return jsonify({"message": "Business detail API"})


@businesses_bp.route("/api/businesses/<business_id>/profiles", methods=["GET", "POST"])
def api_profiles(business_id):
    """Business profiles API."""
    return jsonify({"message": "Profiles API"})


@businesses_bp.route("/api/businesses/<business_id>/profiles/<profile_id>", methods=["PUT", "DELETE"])
def api_profile_detail(business_id, profile_id):
    """Business profile detail API."""
    return jsonify({"message": "Profile detail API"})


@businesses_bp.route("/api/businesses/<business_id>/sync", methods=["POST"])
def api_sync(business_id):
    """Sync business data."""
    return jsonify({"message": "Sync endpoint"})