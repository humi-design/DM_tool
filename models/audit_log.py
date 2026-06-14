"""AuditLog model for tracking system activities."""

from datetime import datetime

from app import db
from models.base import BaseModel


class AuditLog(BaseModel):
    """Audit log model for tracking system activities."""
    
    __tablename__ = "audit_logs"
    
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    action = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    
    resource_type = db.Column(db.String(50), nullable=True, index=True)
    resource_id = db.Column(db.String(36), nullable=True, index=True)
    resource_name = db.Column(db.String(255), nullable=True)
    
    ip_address = db.Column(db.String(45), nullable=True, index=True)
    user_agent = db.Column(db.String(500), nullable=True)
    device_fingerprint = db.Column(db.String(64), nullable=True)
    
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    
    status = db.Column(db.String(50), default="success", nullable=False, index=True)
    error_message = db.Column(db.Text, nullable=True)
    error_code = db.Column(db.String(50), nullable=True)
    
    request_id = db.Column(db.String(36), nullable=True, index=True)
    
    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], back_populates="audit_logs")
    organization = db.relationship("Organization", foreign_keys=[organization_id], back_populates="audit_logs")
    
    __table_args__ = (
        db.Index("idx_audit_user_action_created", "user_id", "action", "created_at"),
        db.Index("idx_audit_action_created", "action", "created_at"),
        db.Index("idx_audit_resource", "resource_type", "resource_id"),
        db.Index("idx_audit_org_category", "organization_id", "category", "created_at"),
        db.Index("idx_audit_ip_created", "ip_address", "created_at"),
        db.Index("idx_audit_status_created", "status", "created_at"),
    )
    
    CATEGORY_AUTH = "authentication"
    CATEGORY_ACCOUNT = "account"
    CATEGORY_ORGANIZATION = "organization"
    CATEGORY_BUSINESS = "business"
    CATEGORY_INSTAGRAM = "instagram"
    CATEGORY_BILLING = "billing"
    CATEGORY_ADMIN = "admin"
    CATEGORY_DATA = "data"
    
    def to_dict(self) -> dict:
        """Convert audit log to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "action": self.action,
            "category": self.category,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def log(
        cls,
        action: str,
        category: str,
        user_id: str = None,
        organization_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        resource_name: str = None,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success",
        error_message: str = None,
        error_code: str = None,
        old_values: dict = None,
        new_values: dict = None,
        request_id: str = None,
    ) -> "AuditLog":
        """Create an audit log entry."""
        log = cls(
            action=action,
            category=category,
            user_id=user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            error_code=error_code,
            old_values=old_values,
            new_values=new_values,
            request_id=request_id,
        )
        db.session.add(log)
        db.session.commit()
        return log