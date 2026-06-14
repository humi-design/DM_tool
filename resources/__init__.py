"""Resources blueprint."""

from flask import Blueprint

resources_bp = Blueprint("resources", __name__)

from resources import routes  # noqa: E402, F401