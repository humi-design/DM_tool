"""DM blueprint."""

from flask import Blueprint

dm_bp = Blueprint("dm", __name__)

from dm import routes  # noqa: E402, F401