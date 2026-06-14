"""Audit middleware for logging user actions."""

from typing import Optional

from flask import Flask, request, g


class AuditMiddleware:
    """Middleware for audit logging."""
    
    AUDIT_ACTIONS = {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }
    
    def __init__(self, app: Flask = None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize the middleware."""
        app.before_request(self.log_request)
        app.after_request(self.log_response)
    
    def log_request(self) -> None:
        """Log incoming request details."""
        g.audit_request_data = {
            "method": request.method,
            "path": request.path,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
        }
    
    def log_response(self, response):
        """Log response details."""
        return response


def log_audit(
    action: str,
    resource_type: str = None,
    resource_id: str = None,
    user_id: str = None,
    organization_id: str = None,
    status: str = "success",
    error_message: str = None,
    old_values: dict = None,
    new_values: dict = None,
) -> None:
    """Log an audit event."""
    from models.audit_log import AuditLog
    
    audit_log = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id or getattr(g, "current_user_id", None),
        organization_id=organization_id or getattr(g, "organization_id", None),
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get("User-Agent", "") if request else None,
        status=status,
        error_message=error_message,
        old_values=old_values,
        new_values=new_values,
    )
    
    from app import db
    db.session.add(audit_log)
    db.session.commit()