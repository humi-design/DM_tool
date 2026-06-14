"""Organizations blueprint."""

from flask import Blueprint

organizations_bp = Blueprint("organizations", __name__)

from organizations import routes  # noqa: E402, F401