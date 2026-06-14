"""Settings blueprint."""

from flask import Blueprint

settings_bp = Blueprint("settings", __name__)

from settings import routes  # noqa: E402, F401