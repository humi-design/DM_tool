"""Users blueprint."""

from flask import Blueprint

users_bp = Blueprint("users", __name__)

from users import routes  # noqa: E402, F401