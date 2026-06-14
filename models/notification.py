"""Notification model for user notifications."""

from datetime import datetime

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Notification(BaseModel, SoftDeleteMixin):
    """Notification model for user notifications."""
    
    __tablename__ = "notifications"
    
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    notification_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    resource_type = db.Column(db.String(50), nullable=True, index=True)
    resource_id = db.Column(db.String(36), nullable=True, index=True)
    
    action_url = db.Column(db.String(500), nullable=True)
    
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True, index=True)
    
    priority = db.Column(db.String(20), default="normal", nullable=False, index=True)
    
    email_sent = db.Column(db.Boolean, default=False, nullable=False, index=True)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    
    push_sent = db.Column(db.Boolean, default=False, nullable=False)
    push_sent_at = db.Column(db.DateTime, nullable=True)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], back_populates="notifications")
    
    __table_args__ = (
        db.Index("idx_notification_user_read", "user_id", "is_read"),
        db.Index("idx_notification_user_priority", "user_id", "priority", "created_at"),
        db.Index("idx_notification_type_created", "notification_type", "created_at"),
        db.Index("idx_notification_resource", "resource_type", "resource_id"),
        db.Index("idx_notification_unread_count", "user_id", "is_read", "created_at"),
    )
    
    TYPE_SYSTEM = "system"
    TYPE_LEAD = "lead"
    TYPE_MESSAGE = "message"
    TYPE_COMMENT = "comment"
    TYPE_INSTAGRAM = "instagram"
    TYPE_BILLING = "billing"
    TYPE_ANALYTICS = "analytics"
    TYPE_REMINDER = "reminder"
    
    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    
    def to_dict(self):
        """Convert notification to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data
    
    def mark_read(self) -> None:
        """Mark notification as read."""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    def mark_unread(self) -> None:
        """Mark notification as unread."""
        self.is_read = False
        self.read_at = None
        db.session.commit()
    
    @classmethod
    def create(
        cls,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        resource_type: str = None,
        resource_id: str = None,
        action_url: str = None,
        priority: str = None,
        metadata: dict = None,
        send_email: bool = False,
        send_push: bool = False,
        expires_at: datetime = None,
    ) -> "Notification":
        """Create a new notification."""
        notification = cls(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            action_url=action_url,
            priority=priority or cls.PRIORITY_NORMAL,
            metadata=metadata or {},
            expires_at=expires_at,
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @classmethod
    def get_unread_count(cls, user_id: str) -> int:
        """Get count of unread notifications."""
        return cls.query.filter_by(
            user_id=user_id,
            is_read=False,
            is_deleted=False,
        ).count()
    
    @classmethod
    def mark_all_read(cls, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        count = cls.query.filter_by(
            user_id=user_id,
            is_read=False,
            is_deleted=False,
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        }, synchronize_session=False)
        db.session.commit()
        return count