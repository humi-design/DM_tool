"""Instagram blueprint."""

from flask import Blueprint

instagram_bp = Blueprint("instagram", __name__)

from instagram import routes  # noqa: E402, F401