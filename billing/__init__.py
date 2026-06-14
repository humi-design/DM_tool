"""Billing blueprint."""

from flask import Blueprint

billing_bp = Blueprint("billing", __name__)

from billing import routes  # noqa: E402, F401