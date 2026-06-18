"""Public marketing pages blueprint."""

from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    """Home page."""
    return render_template("public/home.html")


@public_bp.route("/features")
def features():
    """Features page."""
    return render_template("public/features.html")


@public_bp.route("/how-it-works")
def how_it_works():
    """How it works page."""
    return render_template("public/how-it-works.html")


@public_bp.route("/pricing")
def pricing():
    """Pricing page."""
    return render_template("public/pricing.html")


@public_bp.route("/about")
def about():
    """About page."""
    return render_template("public/about.html")


@public_bp.route("/contact")
def contact():
    """Contact page."""
    return render_template("public/contact.html")


@public_bp.route("/integrations")
def integrations():
    """Integrations page."""
    return render_template("public/integrations.html")


@public_bp.route("/customers")
def customers():
    """Customers page."""
    return render_template("public/customers.html")


@public_bp.route("/use-cases")
def use_cases():
    """Use cases page."""
    return render_template("public/use-cases.html")


@public_bp.route("/demo")
def demo():
    """Interactive demo page."""
    return render_template("public/demo.html")


@public_bp.route("/templates")
def templates():
    """Templates library page."""
    return render_template("public/templates.html")


@public_bp.route("/security")
def security():
    """Security page."""
    return render_template("public/security.html")


@public_bp.route("/faq")
def faq():
    """FAQ page."""
    return render_template("public/faq.html")


@public_bp.route("/blog")
def blog():
    """Blog page."""
    return render_template("public/blog.html")


@public_bp.route("/careers")
def careers():
    """Careers page."""
    return render_template("public/careers.html")


@public_bp.route("/login")
def login():
    """Login page."""
    return render_template("public/login.html")