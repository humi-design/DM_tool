"""Admin routes."""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from functools import wraps

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        # Add your admin check here, e.g.:
        # if not current_user.is_admin:
        #     return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/")
@admin_required
def index():
    """Admin dashboard."""
    return render_template("admin/index.html")


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