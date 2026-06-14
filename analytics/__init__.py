"""Analytics blueprint."""

from flask import Blueprint

analytics_bp = Blueprint("analytics", __name__)

from analytics import routes  # noqa: E402, F401