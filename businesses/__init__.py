"""Businesses blueprint."""

from flask import Blueprint

businesses_bp = Blueprint("businesses", __name__)

from businesses import routes  # noqa: E402, F401