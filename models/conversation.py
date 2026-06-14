"""Conversation and Message models for direct messaging."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Conversation(BaseModel, SoftDeleteMixin):
    """Conversation model for grouping messages between users."""
    
    __tablename__ = "conversations"
    
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    thread_id = db.Column(db.String(100), nullable=False, index=True)
    
    participant_instagram_id = db.Column(db.String(100), nullable=False, index=True)
    participant_username = db.Column(db.String(255), nullable=False, index=True)
    participant_name = db.Column(db.String(255), nullable=True)
    participant_avatar_url = db.Column(db.String(500), nullable=True)
    
    last_message_text = db.Column(db.Text, nullable=True)
    last_message_at = db.Column(db.DateTime, nullable=True, index=True)
    
    messages_count = db.Column(db.Integer, default=0, nullable=False)
    unread_count = db.Column(db.Integer, default=0, nullable=False)
    
    is_spam = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_muted = db.Column(db.Boolean, default=False, nullable=False)
    
    lead_status = db.Column(db.String(50), default="new", nullable=False, index=True)
    lead_priority = db.Column(db.String(50), default="normal", nullable=False, index=True)
    lead_assigned_to = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    lead_tags = db.Column(db.JSON, default=list, nullable=False)
    lead_notes = db.Column(db.Text, nullable=True)
    lead_score = db.Column(db.Integer, nullable=True, index=True)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    instagram_account = db.relationship("InstagramAccount", foreign_keys=[instagram_account_id], back_populates="conversations")
    messages = db.relationship("Message", foreign_keys="Message.conversation_id", back_populates="conversation", lazy="dynamic", cascade="all, delete-orphan")
    assigned_to = db.relationship("User", foreign_keys=[lead_assigned_to])
    
    __table_args__ = (
        db.UniqueConstraint("instagram_account_id", "thread_id", name="uq_conversation_thread"),
        db.UniqueConstraint("instagram_account_id", "participant_instagram_id", name="uq_conversation_participant"),
        db.Index("idx_conv_account_status", "instagram_account_id", "lead_status"),
        db.Index("idx_conv_assigned_priority", "lead_assigned_to", "lead_priority"),
        db.Index("idx_conv_last_message", "last_message_at"),
    )
    
    def to_dict(self):
        """Convert conversation to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data


class Message(BaseModel, SoftDeleteMixin):
    """Message model for individual direct messages."""
    
    __tablename__ = "messages"
    
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    instagram_message_id = db.Column(db.String(100), nullable=False, index=True)
    
    message_type = db.Column(db.String(50), default="text", nullable=False, index=True)
    text = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(500), nullable=True)
    media_type = db.Column(db.String(50), nullable=True)
    
    sender_instagram_id = db.Column(db.String(100), nullable=False, index=True)
    sender_username = db.Column(db.String(255), nullable=True)
    
    is_from_me = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True, index=True)
    
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    
    is_spam = db.Column(db.Boolean, default=False, nullable=False, index=True)
    sentiment_score = db.Column(db.Float, nullable=True, index=True)
    
    is_auto_replied = db.Column(db.Boolean, default=False, nullable=False)
    auto_reply_text = db.Column(db.Text, nullable=True)
    auto_reply_trigger = db.Column(db.String(100), nullable=True)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    conversation = db.relationship("Conversation", foreign_keys=[conversation_id], back_populates="messages")
    
    __table_args__ = (
        db.UniqueConstraint("conversation_id", "instagram_message_id", name="uq_message_instagram"),
        db.Index("idx_message_conv_timestamp", "conversation_id", "timestamp"),
        db.Index("idx_message_sender", "sender_instagram_id", "timestamp"),
        db.Index("idx_message_unread", "conversation_id", "is_read"),
    )
    
    def to_dict(self):
        """Convert message to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data