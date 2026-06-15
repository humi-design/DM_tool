"""Flask application factory for Viraly platform."""

import os
from flask import Flask, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_cors import CORS
from flask_mail import Mail

from config import get_config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
cache = Cache()
mail = Mail()

login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app(config_name: str = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    if hasattr(config_class, "init_app"):
        config_class.init_app(app)
    
    _init_extensions(app)
    _init_middleware(app)
    _init_blueprints(app)
    _init_error_handlers(app)
    _init_health_check(app)
    _init_context_processors(app)
    
    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})


def _init_middleware(app: Flask) -> None:
    """Initialize middleware."""
    from middleware.security import SecurityMiddleware
    from middleware.audit import AuditMiddleware
    
    SecurityMiddleware(app)
    AuditMiddleware(app)


def _init_blueprints(app: Flask) -> None:
    """Initialize blueprints."""
    from auth import auth_bp
    from users import users_bp
    from organizations import organizations_bp
    from businesses import businesses_bp
    from instagram import instagram_bp
    from comments import comments_bp
    from dm import dm_bp
    from resources import resources_bp
    from leads import leads_bp
    from dashboard import dashboard_bp
    from analytics import analytics_bp
    from billing import billing_bp
    from settings import settings_bp
    from admin import admin_bp
    from onboarding import onboarding_bp
    from comment_intelligence import comment_intelligence_bp
    from super_admin import super_admin_bp
    
    # AI DM Employee routes
    try:
        from services.ai_dm_employee.routes import ai_dm_bp
        app.register_blueprint(ai_dm_bp, url_prefix="/api/ai-dm")
    except ImportError:
        pass  # AI DM Employee not available
    
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(organizations_bp, url_prefix="/organizations")
    app.register_blueprint(businesses_bp, url_prefix="/businesses")
    app.register_blueprint(instagram_bp)  # Blueprint already has url_prefix="/instagram"
    app.register_blueprint(comments_bp, url_prefix="/comments")
    app.register_blueprint(dm_bp, url_prefix="/dm")
    app.register_blueprint(resources_bp, url_prefix="/resources")
    app.register_blueprint(leads_bp, url_prefix="/leads")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(onboarding_bp, url_prefix="/onboarding")
    app.register_blueprint(comment_intelligence_bp, url_prefix="/comment-intelligence")
    app.register_blueprint(super_admin_bp, url_prefix="/super-admin")


def _init_error_handlers(app: Flask) -> None:
    """Initialize error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": str(error)}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden", "message": "Access denied"}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": "Resource not found"}), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({"error": "Rate Limit Exceeded", "message": "Too many requests"}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500


def _init_health_check(app: Flask) -> None:
    """Initialize health check endpoint."""
    from datetime import datetime
    
    @app.route("/health")
    def health_check():
        """Public health check endpoint."""
        health = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Database check
        try:
            db.session.execute(db.text("SELECT 1"))
            health["components"]["database"] = "connected"
        except Exception as e:
            health["components"]["database"] = "disconnected"
            health["status"] = "degraded"
        
        # AI providers check
        try:
            from config import Config
            if Config.has_ai_provider():
                health["components"]["ai"] = "configured"
            else:
                health["components"]["ai"] = "not_configured"
        except Exception:
            health["components"]["ai"] = "not_configured"
        
        # OAuth providers check
        try:
            from config import Config
            if Config.has_oauth_provider():
                health["components"]["oauth"] = "configured"
            else:
                health["components"]["oauth"] = "not_configured"
        except Exception:
            health["components"]["oauth"] = "not_configured"
        
        # Payment providers check
        try:
            from config import Config
            if Config.has_payment_provider():
                health["components"]["payments"] = "configured"
            else:
                health["components"]["payments"] = "not_configured"
        except Exception:
            health["components"]["payments"] = "not_configured"
        
        return jsonify(health)
    
    @app.route("/console")
    def console_redirect():
        """Redirect /console to /super-admin for SUPER_ADMIN access."""
        from flask import redirect
        from flask_login import current_user
        
        if current_user.is_authenticated and current_user.is_superuser:
            return redirect("/super-admin")
        return redirect("/auth/login")


def _init_context_processors(app: Flask) -> None:
    """Initialize template context processors."""
    
    @app.context_processor
    def inject_globals():
        from utils.template import site_info
        return {
            "site": site_info,
            "current_year": __import__("datetime").datetime.now().year,
        }
    
    @app.context_processor
    def csrf_token_processor():
        """Inject CSRF token into all templates."""
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    @login_manager.user_loader
    def load_user(user_id: str):
        """Load user for Flask-Login."""
        from models.user import User
        return User.query.get(user_id)