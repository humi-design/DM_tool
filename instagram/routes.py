"""Instagram routes for OAuth, webhooks, and account management."""

import logging
import base64
import json
from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app import db, limiter
from services.instagram_service import (
    get_instagram_service,
    InstagramServiceError,
    AuthenticationError,
    TokenExpiredError,
    APIError,
)
from repositories.instagram_repository import (
    InstagramRepository,
    WebhookLogRepository,
    EventLogRepository,
)
from instagram.webhook import get_webhook_module, WebhookProcessingError

logger = logging.getLogger(__name__)

instagram_bp = Blueprint("instagram", __name__, url_prefix="/instagram")


def get_business_id() -> str:
    """Get current business ID from session or user."""
    if hasattr(current_user, 'current_business_id') and current_user.current_business_id:
        return current_user.current_business_id
    return session.get('current_business_id')


# Rate limiter for webhook endpoint
webhook_limiter = Limiter(key_func=get_remote_address, default_limits=["1000 per minute"])


# ============================================================================
# Webhook Routes (Public)
# ============================================================================

@instagram_bp.route("/webhook", methods=["GET"])
def webhook_verify():
    """Webhook verification endpoint for Meta."""
    service = get_instagram_service()
    
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if service.verify_webhook_mode(mode, token, challenge):
        logger.info("Webhook verified successfully")
        return challenge, 200
    
    logger.warning("Webhook verification failed")
    return "Verification failed", 403


@instagram_bp.route("/webhook", methods=["POST"])
@webhook_limiter.limit("1000 per minute")
def webhook_receive():
    """Receive webhook events from Meta."""
    try:
        payload = request.get_data()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        result = get_webhook_module().process_webhook(payload, signature)
        
        return jsonify({"success": True, **result}), 200
        
    except WebhookProcessingError as e:
        logger.error(f"Webhook processing error: {e.message}")
        if not e.retry:
            return jsonify({"error": e.message}), 400
        return jsonify({"error": "Processing failed, will retry"}), 500
    except Exception as e:
        logger.exception(f"Unexpected webhook error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# OAuth Routes
# ============================================================================

@instagram_bp.route("/oauth/connect", methods=["GET", "POST"])
@login_required
def oauth_connect():
    """Initiate Instagram OAuth connection."""
    business_id = get_business_id()
    
    if not business_id:
        flash("Please select a business first", "warning")
        return redirect(url_for("businesses.index"))
    
    service = get_instagram_service()
    
    if not service.app_id or not service.app_secret:
        flash("Instagram integration is not configured", "error")
        return redirect(url_for("instagram.accounts"))
    
    try:
        # Generate state with business ID
        import secrets
        state_nonce = secrets.token_urlsafe(32)
        state_data = json.dumps({
            "business_id": business_id,
            "user_id": current_user.id,
            "nonce": state_nonce
        })
        state = base64.urlsafe_b64encode(state_data.encode()).decode()
        
        # Store state in session for verification
        session["instagram_oauth_state"] = state
        session["instagram_oauth_business_id"] = business_id
        
        # Get authorization URL
        auth_url = service.get_authorization_url(business_id, state)
        
        return redirect(auth_url)
        
    except Exception as e:
        logger.exception(f"OAuth connect error: {str(e)}")
        flash(f"Failed to initiate connection: {str(e)}", "error")
        return redirect(url_for("instagram.accounts"))


@instagram_bp.route("/oauth/callback", methods=["GET"])
def oauth_callback():
    """Handle OAuth callback from Meta."""
    error = request.args.get("error")
    error_reason = request.args.get("error_reason")
    
    if error:
        logger.warning(f"OAuth error: {error} - {error_reason}")
        flash(f"Authorization failed: {error_reason or error}", "error")
        return redirect(url_for("instagram.accounts"))
    
    code = request.args.get("code")
    state = request.args.get("state")
    
    if not code:
        flash("No authorization code received", "error")
        return redirect(url_for("instagram.accounts"))
    
    # Verify state
    stored_state = session.pop("instagram_oauth_state", None)
    if not state or state != stored_state:
        logger.warning("OAuth state mismatch")
        flash("Invalid OAuth state. Please try again.", "error")
        return redirect(url_for("instagram.accounts"))
    
    business_id = session.pop("instagram_oauth_business_id", None)
    if not business_id:
        business_id = get_business_id()
    
    try:
        service = get_instagram_service()
        result = service.connect_account(business_id, code)
        
        flash("Instagram account connected successfully!", "success")
        return redirect(url_for("instagram.account_detail", account_id=result["account"]["id"]))
        
    except AuthenticationError as e:
        logger.error(f"OAuth authentication error: {e.message}")
        flash(f"Authentication failed: {e.message}", "error")
    except APIError as e:
        logger.error(f"OAuth API error: {e.message}")
        flash(f"Failed to connect: {e.message}", "error")
    except Exception as e:
        logger.exception(f"OAuth callback error: {str(e)}")
        flash(f"Connection failed: {str(e)}", "error")
    
    return redirect(url_for("instagram.accounts"))


@instagram_bp.route("/oauth/disconnect/<account_id>", methods=["POST"])
@login_required
def oauth_disconnect(account_id):
    """Disconnect Instagram account."""
    account = InstagramRepository.get_account_by_id(account_id)
    
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    # Verify ownership
    if account.business_id != get_business_id():
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        service = get_instagram_service()
        service.disconnect_account(account_id)
        
        flash("Instagram account disconnected", "success")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.exception(f"Disconnect error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@instagram_bp.route("/oauth/reconnect/<account_id>", methods=["GET", "POST"])
@login_required
def oauth_reconnect(account_id):
    """Reconnect a disconnected Instagram account."""
    account = InstagramRepository.get_account_by_id(account_id)
    
    if not account:
        flash("Account not found", "error")
        return redirect(url_for("instagram.accounts"))
    
    if request.method == "GET":
        return render_template("instagram/reconnect.html", account=account)
    
    # POST - Initiate reconnection
    try:
        service = get_instagram_service()
        
        # Generate state
        import secrets
        state_nonce = secrets.token_urlsafe(32)
        state_data = json.dumps({
            "account_id": account_id,
            "business_id": account.business_id,
            "user_id": current_user.id,
            "nonce": state_nonce,
            "reconnect": True
        })
        state = base64.urlsafe_b64encode(state_data.encode()).decode()
        
        session["instagram_oauth_state"] = state
        session["instagram_oauth_account_id"] = account_id
        
        auth_url = service.get_authorization_url(account.business_id, state)
        return redirect(auth_url)
        
    except Exception as e:
        logger.exception(f"Reconnect error: {str(e)}")
        flash(f"Failed to reconnect: {str(e)}", "error")
        return redirect(url_for("instagram.accounts"))


# ============================================================================
# Account Management Routes
# ============================================================================

@instagram_bp.route("/accounts")
@login_required
def accounts():
    """List Instagram accounts for the current business."""
    business_id = get_business_id()
    
    if not business_id:
        flash("Please select a business first", "warning")
        return redirect(url_for("businesses.index"))
    
    accounts = InstagramRepository.get_accounts_by_business(business_id)
    
    return render_template(
        "instagram/accounts.html",
        accounts=accounts,
        meta_configured=bool(current_app.config.get("META_APP_ID"))
    )


@instagram_bp.route("/accounts/<account_id>")
@login_required
def account_detail(account_id):
    """Show Instagram account details."""
    account = InstagramRepository.get_account_by_id(account_id)
    
    if not account:
        flash("Account not found", "error")
        return redirect(url_for("instagram.accounts"))
    
    if account.business_id != get_business_id():
        flash("Unauthorized", "error")
        return redirect(url_for("instagram.accounts"))
    
    service = get_instagram_service()
    
    try:
        status = service.get_connection_status(account_id)
    except Exception as e:
        logger.warning(f"Failed to get connection status: {str(e)}")
        status = {"connected": account.is_connected, "token_valid": False, "error": str(e)}
    
    # Get recent event logs
    recent_events = EventLogRepository.get_logs_by_account(account_id, limit=10)
    
    # Get webhook stats
    webhook_stats = WebhookLogRepository.get_stats_by_status(account_id)
    
    return render_template(
        "instagram/account_detail.html",
        account=account,
        status=status,
        recent_events=recent_events,
        webhook_stats=webhook_stats,
    )


@instagram_bp.route("/accounts/<account_id>/sync", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def sync_account(account_id):
    """Sync Instagram account data from Meta API."""
    account = InstagramRepository.get_account_by_id(account_id)
    
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    if account.business_id != get_business_id():
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        service = get_instagram_service()
        info = service.sync_account(account_id)
        
        return jsonify({"success": True, "data": info})
        
    except TokenExpiredError:
        return jsonify({"error": "Token expired. Please reconnect your account.", "code": "token_expired"}), 401
    except Exception as e:
        logger.exception(f"Sync error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@instagram_bp.route("/accounts/<account_id>/status", methods=["GET"])
@login_required
def account_status(account_id):
    """Get account connection status."""
    account = InstagramRepository.get_account_by_id(account_id)
    
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    if account.business_id != get_business_id():
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        service = get_instagram_service()
        status = service.get_connection_status(account_id)
        return jsonify(status)
    except Exception as e:
        logger.exception(f"Status check error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API Routes (JSON)
# ============================================================================

@instagram_bp.route("/api/accounts", methods=["GET"])
@login_required
def api_accounts():
    """Get all Instagram accounts for current business."""
    business_id = get_business_id()
    
    if not business_id:
        return jsonify({"error": "Business not found"}), 400
    
    accounts = InstagramRepository.get_accounts_by_business(business_id)
    
    return jsonify({
        "accounts": [acc.to_dict() for acc in accounts],
        "count": len(accounts),
    })


@instagram_bp.route("/api/accounts/<account_id>", methods=["GET"])
@login_required
def api_account(account_id):
    """Get single Instagram account."""
    account = InstagramRepository.get_account_by_id(account_id)
    
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    if account.business_id != get_business_id():
        return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify(account.to_dict())


@instagram_bp.route("/api/accounts/<account_id>", methods=["DELETE"])
@login_required
def api_delete_account(account_id):
    """Soft delete an Instagram account."""
    account = InstagramRepository.get_account_by_id(account_id)
    
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    if account.business_id != get_business_id():
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        InstagramRepository.soft_delete_account(account_id)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception(f"Delete error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Webhook Logs API
# ============================================================================

@instagram_bp.route("/api/webhook-logs", methods=["GET"])
@login_required
def api_webhook_logs():
    """Get webhook logs with filtering."""
    account_id = request.args.get("account_id")
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    
    # Verify account ownership if specified
    if account_id:
        account = InstagramRepository.get_account_by_id(account_id)
        if not account or account.business_id != get_business_id():
            return jsonify({"error": "Unauthorized"}), 403
        logs = WebhookLogRepository.get_logs_by_account(account_id, limit, offset, status)
    else:
        # Get all logs for business
        accounts = InstagramRepository.get_accounts_by_business(get_business_id())
        account_ids = [acc.id for acc in accounts]
        logs = WebhookLogRepository.get_recent_logs(limit)
        logs = [log for log in logs if log.instagram_account_id in account_ids or not log.instagram_account_id]
    
    return jsonify({
        "logs": [_format_webhook_log(log) for log in logs],
        "count": len(logs),
    })


@instagram_bp.route("/api/webhook-logs/<log_id>", methods=["GET"])
@login_required
def api_webhook_log_detail(log_id):
    """Get detailed webhook log."""
    log = WebhookLogRepository.get_log_by_id(log_id)
    
    if not log:
        return jsonify({"error": "Log not found"}), 404
    
    # Verify ownership
    if log.instagram_account_id:
        account = InstagramRepository.get_account_by_id(log.instagram_account_id)
        if account and account.business_id != get_business_id():
            return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify(_format_webhook_log(log, detail=True))


@instagram_bp.route("/api/webhook-logs/<log_id>/retry", methods=["POST"])
@login_required
def api_retry_webhook(log_id):
    """Retry a failed webhook."""
    log = WebhookLogRepository.get_log_by_id(log_id)
    
    if not log:
        return jsonify({"error": "Log not found"}), 404
    
    if log.processing_status not in ["failed"]:
        return jsonify({"error": "Can only retry failed webhooks"}), 400
    
    try:
        # Re-process
        from instagram.webhook import WebhookRetryHandler
        result = WebhookRetryHandler.process_retries()
        
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception(f"Retry error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Event Logs API
# ============================================================================

@instagram_bp.route("/api/event-logs", methods=["GET"])
@login_required
def api_event_logs():
    """Get event logs with filtering."""
    account_id = request.args.get("account_id")
    event_type = request.args.get("event_type")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    
    if account_id:
        account = InstagramRepository.get_account_by_id(account_id)
        if not account or account.business_id != get_business_id():
            return jsonify({"error": "Unauthorized"}), 403
        logs = EventLogRepository.get_logs_by_account(account_id, limit, offset, event_type)
    else:
        logs = EventLogRepository.get_recent_events(limit)
    
    return jsonify({
        "logs": [_format_event_log(log) for log in logs],
        "count": len(logs),
    })


@instagram_bp.route("/api/event-logs/stats", methods=["GET"])
@login_required
def api_event_stats():
    """Get event statistics."""
    account_id = request.args.get("account_id")
    days = int(request.args.get("days", 30))
    
    if account_id:
        account = InstagramRepository.get_account_by_id(account_id)
        if not account or account.business_id != get_business_id():
            return jsonify({"error": "Unauthorized"}), 403
    
    stats = EventLogRepository.get_event_stats(account_id, days)
    return jsonify(stats)


# ============================================================================
# Helper Functions
# ============================================================================

def _format_webhook_log(log, detail: bool = False) -> Dict[str, Any]:
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


def _format_event_log(log) -> Dict[str, Any]:
    """Format event log for JSON response."""
    return {
        "id": log.id,
        "event_id": log.event_id,
        "event_type": log.event_type,
        "event_subtype": log.event_subtype,
        "sender_id": log.sender_id,
        "recipient_id": log.recipient_id,
        "message_id": log.message_id,
        "comment_id": log.comment_id,
        "status": log.status,
        "event_time": log.event_time.isoformat() if log.event_time else None,
        "processed_at": log.processed_at.isoformat() if log.processed_at else None,
        "error_message": log.error_message,
        "instagram_account_id": log.instagram_account_id,
    }