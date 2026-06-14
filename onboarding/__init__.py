"""Onboarding module for AI-first user onboarding."""
from flask import Blueprint

onboarding_bp = Blueprint("onboarding", __name__, 
                          url_prefix="/onboarding",
                          template_folder="../templates/onboarding",
                          static_folder="../static")

from onboarding import routes  # noqa: E402, F401