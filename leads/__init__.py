"""Leads blueprint."""

from flask import Blueprint

leads_bp = Blueprint("leads", __name__)

from leads import routes  # noqa: E402, F401