"""Instagram models."""

from datetime import datetime
import uuid

from app import db
from models.base import BaseModel, SoftDeleteMixin


class InstagramAccount(BaseModel, SoftDeleteMixin):
    """Instagram account model."""
    
    __tablename__ = "instagram_accounts"
    
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    business_profile_id = db.Column(
        db.String(36),
        db.ForeignKey("business_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Meta API identifiers
    instagram_user_id = db.Column(db.String(100), nullable=False, index=True)
    facebook_page_id = db.Column(db.String(100), nullable=True, index=True)
    meta_user_id = db.Column(db.String(100), nullable=True, index=True)
    
    username = db.Column(db.String(255), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=True)
    biography = db.Column(db.Text, nullable=True)
    profile_picture_url = db.Column(db.String(500), nullable=True)
    
    followers_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    media_count = db.Column(db.Integer, default=0)
    
    is_business = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_connected = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Secure token storage (encrypted)
    access_token = db.Column(db.String(1000), nullable=True)
    refresh_token = db.Column(db.String(500), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True, index=True)
    token_scope = db.Column(db.String(500), nullable=True)
    
    last_synced_at = db.Column(db.DateTime, nullable=True, index=True)
    last_activity_at = db.Column(db.DateTime, nullable=True, index=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="instagram_accounts")
    business_profile = db.relationship("BusinessProfile", foreign_keys=[business_profile_id], back_populates="instagram_accounts")
    comments = db.relationship("Comment", foreign_keys="Comment.instagram_account_id", back_populates="instagram_account", lazy="dynamic", cascade="all, delete-orphan")
    conversations = db.relationship("Conversation", foreign_keys="Conversation.instagram_account_id", back_populates="instagram_account", lazy="dynamic", cascade="all, delete-orphan")
    webhook_logs = db.relationship("WebhookLog", back_populates="instagram_account", lazy="dynamic", cascade="all, delete-orphan")
    event_logs = db.relationship("EventLog", back_populates="instagram_account", lazy="dynamic", cascade="all, delete-orphan")
    ai_processing_logs = db.relationship("AIProcessingLog", back_populates="instagram_account", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.UniqueConstraint("business_id", "instagram_user_id", name="uq_instagram_business_user"),
        db.Index("idx_ig_account_business_active", "business_id", "is_active"),
        db.Index("idx_ig_account_username", "username", "is_connected"),
    )
    
    def to_dict(self, include_tokens: bool = False):
        """Convert to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        if not include_tokens:
            data.pop("access_token", None)
            data.pop("refresh_token", None)
        return data
    
    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at
    
    def needs_token_refresh(self) -> bool:
        """Check if token should be refreshed."""
        if not self.token_expires_at:
            return False
        # Refresh if expires within 1 hour
        from datetime import timedelta
        return datetime.utcnow() >= (self.token_expires_at - timedelta(hours=1))


class WebhookLog(BaseModel):
    """Webhook event log for debugging and auditing."""
    
    __tablename__ = "instagram_webhook_logs"
    
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Event metadata
    event_type = db.Column(db.String(100), nullable=False, index=True)
    event_id = db.Column(db.String(255), nullable=True, index=True)
    webhook_url = db.Column(db.String(500), nullable=True)
    
    # Request details
    request_method = db.Column(db.String(10), nullable=False)
    request_headers = db.Column(db.Text, nullable=True)
    request_ip = db.Column(db.String(45), nullable=True)
    request_user_agent = db.Column(db.String(500), nullable=True)
    
    # Payload storage
    raw_payload = db.Column(db.Text, nullable=False)
    parsed_payload = db.Column(db.Text, nullable=True)
    
    # Processing status
    signature_valid = db.Column(db.Boolean, nullable=True)
    signature_validation_error = db.Column(db.String(500), nullable=True)
    processing_status = db.Column(
        db.String(50),
        nullable=False,
        default="received",
        index=True
    )  # received, processing, processed, failed, duplicate
    processing_error = db.Column(db.Text, nullable=True)
    
    # Idempotency
    is_duplicate = db.Column(db.Boolean, default=False, nullable=False, index=True)
    duplicate_of_id = db.Column(db.String(36), nullable=True)
    
    # Timing
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    processing_duration_ms = db.Column(db.Integer, nullable=True)
    
    # Retry tracking
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    last_retry_at = db.Column(db.DateTime, nullable=True)
    next_retry_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Relationships
    instagram_account = db.relationship("InstagramAccount", foreign_keys=[instagram_account_id], back_populates="webhook_logs")
    event_logs = db.relationship("EventLog", back_populates="webhook_log", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index("idx_webhook_log_status_time", "processing_status", "received_at"),
        db.Index("idx_webhook_log_event_type", "event_type", "received_at"),
    )
    
    def mark_processed(self, success: bool = True, error: str = None):
        """Mark webhook as processed."""
        from datetime import datetime as dt
        self.processed_at = dt.utcnow()
        if success:
            self.processing_status = "processed"
            self.processing_error = None
        else:
            self.processing_status = "failed"
            self.processing_error = error
        if self.received_at:
            self.processing_duration_ms = int((self.processed_at - self.received_at).total_seconds() * 1000)
    
    def mark_duplicate(self, original_id: str):
        """Mark webhook as duplicate."""
        self.is_duplicate = True
        self.duplicate_of_id = original_id
        self.processing_status = "duplicate"
    
    def increment_retry(self):
        """Increment retry count."""
        from datetime import timedelta
        self.retry_count += 1
        self.last_retry_at = datetime.utcnow()
        # Exponential backoff: 1min, 5min, 15min, 1hour
        backoff_minutes = [1, 5, 15, 60][min(self.retry_count - 1, 3)]
        self.next_retry_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)


class EventLog(BaseModel):
    """Processed event log for business intelligence."""
    
    __tablename__ = "instagram_event_logs"
    
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    webhook_log_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_webhook_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Event identification (for idempotency)
    event_id = db.Column(db.String(255), nullable=True, index=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)
    event_subtype = db.Column(db.String(100), nullable=True, index=True)
    
    # Event data
    sender_id = db.Column(db.String(100), nullable=True, index=True)
    recipient_id = db.Column(db.String(100), nullable=True, index=True)
    message_id = db.Column(db.String(255), nullable=True, index=True)
    media_id = db.Column(db.String(255), nullable=True)
    comment_id = db.Column(db.String(255), nullable=True)
    
    # Parsed event data
    event_data = db.Column(db.Text, nullable=True)
    
    # Processing status
    status = db.Column(
        db.String(50),
        nullable=False,
        default="processed",
        index=True
    )  # processed, failed, skipped
    
    # Timestamps
    event_time = db.Column(db.DateTime, nullable=False, index=True)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Error handling
    error_message = db.Column(db.Text, nullable=True)
    
    # Relationships
    instagram_account = db.relationship("InstagramAccount", foreign_keys=[instagram_account_id], back_populates="event_logs")
    webhook_log = db.relationship("WebhookLog", foreign_keys=[webhook_log_id], back_populates="event_logs")
    
    __table_args__ = (
        db.UniqueConstraint("event_id", name="uq_event_log_event_id"),
        db.Index("idx_event_log_account_type", "instagram_account_id", "event_type"),
        db.Index("idx_event_log_time", "event_time"),
    )
    
    @classmethod
    def is_duplicate_event(cls, event_id: str) -> bool:
        """Check if event has already been processed."""
        if not event_id:
            return False
        return cls.query.filter_by(event_id=event_id).first() is not None