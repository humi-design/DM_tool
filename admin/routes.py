"""Admin routes."""

import os
import json
import uuid
from functools import wraps
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app, g, flash
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from models.user import User
from models.organization import Organization
from models.audit_log import AuditLog
from utils.jwt import jwt_required, get_current_user_id, JWTManager

admin_bp = Blueprint("admin", __name__)


# Hardcoded admin credentials (can be overridden via environment variables)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@dmtool.local')


def get_user_from_token():
    """Get user from JWT token in Authorization header or cookie."""
    user_id = None
    
    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = JWTManager.verify_access_token(token)
        if payload:
            user_id = payload.get("sub")
    
    # Fallback to cookie
    if not user_id:
        token = request.cookies.get("access_token")
        if token:
            payload = JWTManager.verify_access_token(token)
            if payload:
                user_id = payload.get("sub")
    
    if user_id:
        return User.query.get(user_id)
    return None


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get current user
        user = get_user_from_token()
        
        if not user:
            # Try Flask-Login
            if not current_user.is_authenticated:
                return redirect(url_for('admin.login'))
            user = current_user
        
        # Check if user is superuser
        if not user.is_superuser:
            return jsonify({"error": "Admin access required"}), 403
        
        # Store user in request context
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def get_current_admin():
    """Get the current admin user."""
    user = get_user_from_token()
    if not user:
        user = current_user if current_user.is_authenticated else None
    return user


# =============================================================================
# Login/Logout
# =============================================================================

@admin_bp.route("/login", methods=['GET', 'POST'])
def login():
    """Admin login page with hardcoded credentials."""
    if request.method == 'GET':
        # If already logged in as admin, redirect to dashboard
        if current_user.is_authenticated and current_user.is_superuser:
            return redirect(url_for('admin.index'))
        return render_template("admin/login.html")
    
    # Handle POST - verify credentials
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # Find or create admin user
        admin_user = User.query.filter_by(email=ADMIN_EMAIL).first()
        
        if not admin_user:
            # Create a new admin user
            admin_user = User(
                id=str(uuid.uuid4()),
                email=ADMIN_EMAIL,
                username=ADMIN_USERNAME,
                full_name='Admin',
                password_hash=generate_password_hash(password),
                is_verified=True,
                is_superuser=True,
                is_active=True,
            )
            db.session.add(admin_user)
            
            # Create default organization for admin
            org = Organization(
                id=str(uuid.uuid4()),
                name='Admin Organization',
                slug='admin-org',
                owner_id=admin_user.id,
                plan='enterprise',
                plan_expires_at=datetime.utcnow() + timedelta(days=365 * 10),
                is_active=True,
            )
            db.session.add(org)
            db.session.commit()
            
            admin_user.organization_id = org.id
            db.session.commit()
        else:
            # Update user to be superuser
            admin_user.is_superuser = True
            admin_user.is_verified = True
            admin_user.is_active = True
            db.session.commit()
        
        # Log in the user
        login_user(admin_user, remember=True)
        
        flash('Welcome to Admin Panel!', 'success')
        return redirect(url_for('admin.index'))
    
    flash('Invalid credentials. Please try again.', 'danger')
    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=['POST'])
def logout():
    """Admin logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin.login'))


# =============================================================================
# Dashboard
# =============================================================================

@admin_bp.route("/")
@admin_required
def index():
    """Admin dashboard."""
    return render_template("admin/index.html")


@admin_bp.route("/settings")
@admin_required
def settings():
    """Admin settings page - API keys and configuration."""
    return render_template("admin/settings.html")


@admin_bp.route("/users")
@admin_required
def users():
    """User management page."""
    return render_template("admin/users.html")


@admin_bp.route("/organizations")
@admin_required
def organizations():
    """Organization management page."""
    return render_template("admin/organizations.html")


@admin_bp.route("/subscriptions")
@admin_required
def subscriptions():
    """Subscription management page."""
    return render_template("admin/subscriptions.html")


@admin_bp.route("/audit-logs")
@admin_required
def audit_logs():
    """Audit logs page."""
    return render_template("admin/audit_logs.html")


@admin_bp.route("/system")
@admin_required
def system():
    """System status page."""
    return render_template("admin/system.html")


@admin_bp.route("/instagram-diagnostics")
@admin_required
def instagram_diagnostics():
    """Instagram webhook and event diagnostics page."""
    from repositories.instagram_repository import WebhookLogRepository, EventLogRepository, InstagramRepository
    
    # Get statistics
    webhook_stats = {
        "total": 0,
        "by_status": WebhookLogRepository.get_stats_by_status(),
        "recent": WebhookLogRepository.get_recent_logs(20)
    }
    
    event_stats = EventLogRepository.get_event_stats(days=30)
    recent_events = EventLogRepository.get_recent_events(20)
    
    # Get accounts
    accounts = InstagramRepository.get_connected_accounts()
    
    # Calculate totals
    webhook_stats["total"] = sum(webhook_stats["by_status"].values())
    
    return render_template(
        "admin/instagram_diagnostics.html",
        webhook_stats=webhook_stats,
        event_stats=event_stats,
        recent_events=recent_events,
        accounts=accounts
    )


# =============================================================================
# API Keys Management
# =============================================================================

@admin_bp.route("/api/settings/keys", methods=["GET"])
@admin_required
def get_api_keys():
    """Get current API keys configuration (masked)."""
    keys = {
        # AI Provider Keys
        "ai_providers": {
            "openai": _mask_key(os.environ.get("AI_OPENAI_API_KEY", "")),
            "anthropic": _mask_key(os.environ.get("AI_ANTHROPIC_API_KEY", "")),
            "gemini": _mask_key(os.environ.get("AI_GEMINI_API_KEY", "")),
            "ollama": os.environ.get("AI_OLLAMA_BASE_URL", ""),
            "mistral": _mask_key(os.environ.get("AI_MISTRAL_API_KEY", "")),
            "qwen": _mask_key(os.environ.get("AI_QWEN_API_KEY", "")),
        },
        # Instagram/Meta Keys
        "instagram": {
            "app_id": _mask_key(os.environ.get("INSTAGRAM_APP_ID", "")),
            "app_secret": _mask_key(os.environ.get("INSTAGRAM_APP_SECRET", "")),
            "webhook_verify_token": _mask_key(os.environ.get("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "")),
        },
        # Billing Keys
        "billing": {
            "stripe_key": _mask_key(os.environ.get("STRIPE_SECRET_KEY", "")),
            "razorpay_key": _mask_key(os.environ.get("RAZORPAY_KEY_ID", "")),
            "razorpay_secret": _mask_key(os.environ.get("RAZORPAY_KEY_SECRET", "")),
        },
        # Email Keys
        "email": {
            "sendgrid_key": _mask_key(os.environ.get("SENDGRID_API_KEY", "")),
            "smtp_host": os.environ.get("SMTP_HOST", ""),
            "smtp_port": os.environ.get("SMTP_PORT", ""),
            "smtp_user": os.environ.get("SMTP_USERNAME", ""),
            "smtp_password": _mask_key(os.environ.get("SMTP_PASSWORD", "")),
        },
        # Database (masked)
        "database": {
            "url": _mask_key(os.environ.get("DATABASE_URL", ""), show_chars=10),
        },
        # App Config
        "app": {
            "secret_key": _mask_key(current_app.config.get("SECRET_KEY", ""), show_chars=8),
            "debug": current_app.config.get("DEBUG", False),
            "environment": os.environ.get("FLASK_ENV", "production"),
        }
    }
    return jsonify(keys)


@admin_bp.route("/api/settings/keys", methods=["POST"])
@admin_required
def save_api_keys():
    """Save API keys to environment file."""
    data = request.get_json()
    user = getattr(request, 'current_user', None) or get_current_admin()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Build .env file content
    env_lines = []
    
    # AI Providers
    if data.get("ai_providers"):
        ap = data["ai_providers"]
        if ap.get("openai"):
            env_lines.append(f'AI_OPENAI_API_KEY="{ap["openai"]}"')
        if ap.get("anthropic"):
            env_lines.append(f'AI_ANTHROPIC_API_KEY="{ap["anthropic"]}"')
        if ap.get("gemini"):
            env_lines.append(f'AI_GEMINI_API_KEY="{ap["gemini"]}"')
        if ap.get("ollama"):
            env_lines.append(f'AI_OLLAMA_BASE_URL="{ap["ollama"]}"')
        if ap.get("mistral"):
            env_lines.append(f'AI_MISTRAL_API_KEY="{ap["mistral"]}"')
        if ap.get("qwen"):
            env_lines.append(f'AI_QWEN_API_KEY="{ap["qwen"]}"')
    
    # Instagram
    if data.get("instagram"):
        ig = data["instagram"]
        if ig.get("app_id"):
            env_lines.append(f'INSTAGRAM_APP_ID="{ig["app_id"]}"')
        if ig.get("app_secret"):
            env_lines.append(f'INSTAGRAM_APP_SECRET="{ig["app_secret"]}"')
        if ig.get("webhook_verify_token"):
            env_lines.append(f'INSTAGRAM_WEBHOOK_VERIFY_TOKEN="{ig["webhook_verify_token"]}"')
    
    # Billing
    if data.get("billing"):
        bill = data["billing"]
        if bill.get("stripe_key"):
            env_lines.append(f'STRIPE_SECRET_KEY="{bill["stripe_key"]}"')
        if bill.get("razorpay_key"):
            env_lines.append(f'RAZORPAY_KEY_ID="{bill["razorpay_key"]}"')
        if bill.get("razorpay_secret"):
            env_lines.append(f'RAZORPAY_KEY_SECRET="{bill["razorpay_secret"]}"')
    
    # Email
    if data.get("email"):
        em = data["email"]
        if em.get("sendgrid_key"):
            env_lines.append(f'SENDGRID_API_KEY="{em["sendgrid_key"]}"')
        if em.get("smtp_host"):
            env_lines.append(f'SMTP_HOST="{em["smtp_host"]}"')
        if em.get("smtp_port"):
            env_lines.append(f'SMTP_PORT="{em["smtp_port"]}"')
        if em.get("smtp_user"):
            env_lines.append(f'SMTP_USERNAME="{em["smtp_user"]}"')
        if em.get("smtp_password"):
            env_lines.append(f'SMTP_PASSWORD="{em["smtp_password"]}"')
    
    # Write to .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        with open(env_path, "a") as f:
            f.write("\n# API Keys (updated via admin panel)\n")
            f.write("\n".join(env_lines) + "\n")
        
        # Also update current environment
        for line in env_lines:
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                os.environ[key] = value
        
        # Log the action
        if user:
            AuditLog.log(
                action="api_keys_updated",
                category=AuditLog.CATEGORY_ADMIN,
                user_id=user.id,
                details={"updated_sections": list(data.keys())}
            )
        
        return jsonify({"success": True, "message": "API keys saved to .env file"})
    except Exception as e:
        return jsonify({"error": f"Failed to save keys: {str(e)}"}), 500


@admin_bp.route("/api/settings/demo-data", methods=["POST"])
@admin_required
def create_demo_data():
    """Create demo/test data for testing the application."""
    from models.organization import Organization
    from models.subscription import Subscription
    from models.plan import Plan, OrganizationFeature
    from datetime import datetime, timedelta
    import uuid
    
    user = getattr(request, 'current_user', None) or get_current_admin()
    
    try:
        # Create demo organization
        demo_org = Organization(
            id=str(uuid.uuid4()),
            name="Demo Company",
            slug="demo-company-" + str(uuid.uuid4())[:8],
            description="Demo organization for testing",
            owner_id=user.id if user else None,
            plan="starter",
            plan_expires_at=datetime.utcnow() + timedelta(days=30),
            is_active=True,
        )
        db.session.add(demo_org)
        
        # Update user profile if needed
        if user and not user.organization_id:
            user.organization_id = demo_org.id
        
        # Create demo subscription
        subscription = Subscription(
            id=str(uuid.uuid4()),
            organization_id=demo_org.id,
            plan_id="starter",
            plan_name="Starter",
            status="active",
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30),
            quantity=1,
            unit_price=0,
            total_amount=0,
        )
        db.session.add(subscription)
        
        db.session.commit()
        
        # Log the action
        if user:
            AuditLog.log(
                action="demo_data_created",
                category=AuditLog.CATEGORY_ADMIN,
                user_id=user.id,
                details={"organization_id": demo_org.id}
            )
        
        return jsonify({
            "success": True,
            "message": "Demo data created successfully",
            "data": {
                "organization_id": demo_org.id,
                "organization_name": demo_org.name,
                "subscription_status": subscription.status,
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create demo data: {str(e)}"}), 500


@admin_bp.route("/api/settings/test-login", methods=["POST"])
@admin_required
def test_login():
    """Create a test user and return credentials."""
    from services.auth_service import AuthService
    
    data = request.get_json() or {}
    email = data.get("email", "test@example.com")
    password = data.get("password", "TestPass123!")
    
    try:
        # Create test user
        result = AuthService.register(
            email=email,
            password=password,
            first_name="Test",
            last_name="User",
            organization_name="Test Organization",
        )
        
        if result.success:
            # Create test organization
            from models.organization import Organization
            from datetime import datetime, timedelta
            import uuid
            
            org = Organization(
                id=str(uuid.uuid4()),
                name="Test Organization",
                slug="test-org-" + str(uuid.uuid4())[:8],
                owner_id=result.user.id,
                plan="starter",
                plan_expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True,
            )
            db.session.add(org)
            
            # Update user
            result.user.organization_id = org.id
            result.user.is_verified = True
            result.user.is_superuser = True
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Test user created",
                "credentials": {
                    "email": email,
                    "password": password,
                    "user_id": result.user.id,
                    "organization_id": org.id,
                }
            })
        else:
            # User might already exist, try to login
            login_result = AuthService.login(email=email, password=password)
            if login_result.success:
                return jsonify({
                    "success": True,
                    "message": "Test user already exists, returning credentials",
                    "credentials": {
                        "email": email,
                        "password": password,
                    }
                })
            return jsonify({"error": result.error}), 400
            
    except Exception as e:
        return jsonify({"error": f"Failed to create test user: {str(e)}"}), 500


# =============================================================================
# Existing Admin APIs
# =============================================================================

@admin_bp.route("/api/users", methods=["GET"])
@admin_required
def api_users():
    """Admin users API."""
    return jsonify({"message": "Admin users API"})


@admin_bp.route("/api/users/<user_id>", methods=["PUT", "DELETE"])
@admin_required
def api_user_detail(user_id):
    """Admin user detail API."""
    return jsonify({"message": "Admin user detail API"})


@admin_bp.route("/api/organizations", methods=["GET"])
@admin_required
def api_organizations():
    """Admin organizations API."""
    return jsonify({"message": "Admin organizations API"})


@admin_bp.route("/api/organizations/<org_id>", methods=["PUT", "DELETE"])
@admin_required
def api_org_detail(org_id):
    """Admin org detail API."""
    return jsonify({"message": "Admin org detail API"})


@admin_bp.route("/api/audit-logs", methods=["GET"])
@admin_required
def api_audit_logs():
    """Audit logs API."""
    return jsonify({"message": "Audit logs API"})


@admin_bp.route("/api/stats", methods=["GET"])
@admin_required
def api_stats():
    """Admin stats API."""
    return jsonify({"message": "Admin stats API"})


@admin_bp.route("/api/system/status", methods=["GET"])
@admin_required
def api_system_status():
    """System status API."""
    return jsonify({"message": "System status API"})


@admin_bp.route("/api/instagram/webhooks", methods=["GET"])
@admin_required
def api_instagram_webhooks():
    """Get webhook logs for admin diagnostics."""
    from repositories.instagram_repository import WebhookLogRepository
    
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    status = request.args.get("status")
    
    logs = WebhookLogRepository.get_recent_logs(limit)
    if status:
        logs = [log for log in logs if log.processing_status == status]
    
    return jsonify({
        "logs": [_format_webhook_log(log) for log in logs],
        "stats": WebhookLogRepository.get_stats_by_status()
    })


@admin_bp.route("/api/instagram/webhooks/<log_id>", methods=["GET"])
@admin_required
def api_instagram_webhook_detail(log_id):
    """Get detailed webhook log."""
    from repositories.instagram_repository import WebhookLogRepository
    
    log = WebhookLogRepository.get_log_by_id(log_id)
    if not log:
        return jsonify({"error": "Log not found"}), 404
    
    return jsonify(_format_webhook_log(log, detail=True))


@admin_bp.route("/api/instagram/webhooks/<log_id>/retry", methods=["POST"])
@admin_required
def api_instagram_webhook_retry(log_id):
    """Retry a failed webhook."""
    from repositories.instagram_repository import WebhookLogRepository
    from instagram.webhook import WebhookRetryHandler
    from app import db
    
    log = WebhookLogRepository.get_log_by_id(log_id)
    if not log:
        return jsonify({"error": "Log not found"}), 404
    
    if log.processing_status not in ["failed"]:
        return jsonify({"error": "Can only retry failed webhooks"}), 400
    
    try:
        log.increment_retry()
        db.session.commit()
        return jsonify({"success": True, "retry_count": log.retry_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/instagram/events", methods=["GET"])
@admin_required
def api_instagram_events():
    """Get event logs for admin diagnostics."""
    from repositories.instagram_repository import EventLogRepository
    
    limit = min(int(request.args.get("limit", 50)), 200)
    days = int(request.args.get("days", 30))
    
    stats = EventLogRepository.get_event_stats(days=days)
    recent = EventLogRepository.get_recent_events(limit)
    
    return jsonify({
        "stats": stats,
        "events": [_format_event_log(event) for event in recent]
    })


def _mask_key(key, show_chars: int = 4) -> str:
    """Mask an API key, showing only the last few characters."""
    if not key:
        return ""
    # Convert bytes to string if needed
    if isinstance(key, bytes):
        key = key.decode('utf-8', errors='replace')
    key = str(key)
    if len(key) <= show_chars:
        return "*" * len(key)
    return "*" * (len(key) - show_chars) + key[-show_chars:]


def _format_webhook_log(log, detail: bool = False):
    """Format webhook log for JSON response."""
    result = {
        "id": log.id,
        "event_type": log.event_type,
        "event_id": log.event_id,
        "processing_status": log.processing_status,
        "signature_valid": log.signature_valid,
        "is_duplicate": log.is_duplicate,
        "retry_count": log.retry_count,
        "received_at": log.received_at.isoformat() if log.received_at else None,
        "processed_at": log.processed_at.isoformat() if log.processed_at else None,
        "processing_duration_ms": log.processing_duration_ms,
        "processing_error": log.processing_error,
        "instagram_account_id": log.instagram_account_id,
    }
    
    if detail:
        result.update({
            "request_method": log.request_method,
            "request_ip": log.request_ip,
            "request_user_agent": log.request_user_agent,
            "raw_payload": log.raw_payload,
            "parsed_payload": log.parsed_payload,
            "webhook_url": log.webhook_url,
            "next_retry_at": log.next_retry_at.isoformat() if log.next_retry_at else None,
        })
    
    return result


def _format_event_log(log):
    """Format event log for JSON response."""
    return {
        "id": log.id,
        "event_id": log.event_id,
        "event_type": log.event_type,
        "event_subtype": log.event_subtype,
        "sender_id": log.sender_id,
        "recipient_id": log.recipient_id,
        "status": log.status,
        "event_time": log.event_time.isoformat() if log.event_time else None,
        "processed_at": log.processed_at.isoformat() if log.processed_at else None,
        "error_message": log.error_message,
        "instagram_account_id": log.instagram_account_id,
    }