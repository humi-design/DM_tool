"""Instagram blueprint for Meta Graph API integration."""

from flask import Blueprint

instagram_bp = Blueprint("instagram", __name__)

from instagram import routes, webhook  # noqa: E402, F401