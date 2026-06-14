"""Instagram models."""

from datetime import datetime
import uuid

from app import db
from models.base import BaseModel, SoftDeleteMixin


class InstagramAccount(BaseModel, SoftDeleteMixin):
    """Instagram account model."""
    
    __tablename__ = "instagram_accounts"
    
    business_profile_id = db.Column(
        db.String(36),
        db.ForeignKey("business_profiles.id"),
        nullable=False
    )
    
    instagram_user_id = db.Column(db.String(100), nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=True)
    biography = db.Column(db.Text, nullable=True)
    profile_picture_url = db.Column(db.String(500), nullable=True)
    
    followers_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    media_count = db.Column(db.Integer, default=0)
    
    is_business = db.Column(db.Boolean, default=False)
    is_connected = db.Column(db.Boolean, default=True)
    
    access_token = db.Column(db.String(500), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    
    last_synced_at = db.Column(db.DateTime, nullable=True)
    last_activity_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self, include_tokens: bool = False):
        """Convert to dictionary."""
        data = super().to_dict()
        if not include_tokens:
            data.pop("access_token", None)
        return data


class InstagramPost(BaseModel, SoftDeleteMixin):
    """Instagram post model."""
    
    __tablename__ = "instagram_posts"
    
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id"),
        nullable=False
    )
    
    instagram_media_id = db.Column(db.String(100), nullable=False, index=True)
    instagram_permalink = db.Column(db.String(500), nullable=True)
    
    caption = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(50), nullable=True)
    media_url = db.Column(db.String(500), nullable=True)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    
    like_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    saves_count = db.Column(db.Integer, default=0)
    
    reach = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    
    timestamp = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    
    hashtags = db.Column(db.JSON, default=list, nullable=False)
    mentions = db.Column(db.JSON, default=list, nullable=False)
    
    is_published = db.Column(db.Boolean, default=True)
    is_scheduled = db.Column(db.Boolean, default=False)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    
    metadata = db.Column(db.JSON, default=dict, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        return data


class InstagramComment(BaseModel, SoftDeleteMixin):
    """Instagram comment model."""
    
    __tablename__ = "instagram_comments"
    
    instagram_post_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_posts.id"),
        nullable=False
    )
    
    instagram_comment_id = db.Column(db.String(100), nullable=False, index=True)
    parent_comment_id = db.Column(db.String(100), nullable=True)
    
    text = db.Column(db.Text, nullable=False)
    
    instagram_user_id = db.Column(db.String(100), nullable=True)
    instagram_username = db.Column(db.String(255), nullable=True)
    instagram_profile_picture = db.Column(db.String(500), nullable=True)
    
    like_count = db.Column(db.Integer, default=0)
    
    timestamp = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    
    is_reply = db.Column(db.Boolean, default=False)
    is_hidden = db.Column(db.Boolean, default=False)
    is_spam = db.Column(db.Boolean, default=False)
    
    sentiment_score = db.Column(db.Float, nullable=True)
    
    auto_reply_enabled = db.Column(db.Boolean, default=False)
    auto_reply_text = db.Column(db.Text, nullable=True)
    
    metadata = db.Column(db.JSON, default=dict, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        return data


class InstagramDM(BaseModel, SoftDeleteMixin):
    """Instagram direct message model."""
    
    __tablename__ = "instagram_dms"
    
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id"),
        nullable=False
    )
    
    thread_id = db.Column(db.String(100), nullable=False, index=True)
    message_id = db.Column(db.String(100), nullable=False, index=True)
    
    instagram_user_id = db.Column(db.String(100), nullable=True)
    instagram_username = db.Column(db.String(255), nullable=True)
    instagram_profile_picture = db.Column(db.String(500), nullable=True)
    
    message_type = db.Column(db.String(50), default="text", nullable=False)
    text = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(500), nullable=True)
    
    is_from_me = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    timestamp = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    
    is_spam = db.Column(db.Boolean, default=False)
    sentiment_score = db.Column(db.Float, nullable=True)
    
    is_auto_replied = db.Column(db.Boolean, default=False)
    auto_reply_text = db.Column(db.Text, nullable=True)
    
    lead_status = db.Column(db.String(50), default="new", nullable=False)
    lead_tags = db.Column(db.JSON, default=list, nullable=False)
    lead_notes = db.Column(db.Text, nullable=True)
    
    metadata = db.Column(db.JSON, default=dict, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        return data


class DMThread(BaseModel, SoftDeleteMixin):
    """DM thread model for grouping messages."""
    
    __tablename__ = "dm_threads"
    
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id"),
        nullable=False
    )
    
    thread_id = db.Column(db.String(100), nullable=False, index=True)
    
    instagram_user_id = db.Column(db.String(100), nullable=True)
    instagram_username = db.Column(db.String(255), nullable=True)
    instagram_profile_picture = db.Column(db.String(500), nullable=True)
    
    last_message_text = db.Column(db.Text, nullable=True)
    last_message_at = db.Column(db.DateTime, nullable=True)
    
    messages_count = db.Column(db.Integer, default=0)
    unread_count = db.Column(db.Integer, default=0)
    
    is_spam = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    
    lead_status = db.Column(db.String(50), default="new", nullable=False)
    lead_priority = db.Column(db.String(50), default="normal", nullable=False)
    lead_assigned_to = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    
    lead_tags = db.Column(db.JSON, default=list, nullable=False)
    lead_notes = db.Column(db.Text, nullable=True)
    
    metadata = db.Column(db.JSON, default=dict, nullable=False)
    
    def to_dict(self):
        """Convert to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        return data