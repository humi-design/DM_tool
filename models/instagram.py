"""Instagram models."""

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
    
    instagram_user_id = db.Column(db.String(100), nullable=False, index=True)
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
    
    access_token = db.Column(db.String(500), nullable=True)
    refresh_token = db.Column(db.String(500), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True, index=True)
    
    last_synced_at = db.Column(db.DateTime, nullable=True, index=True)
    last_activity_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Relationships
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="instagram_accounts")
    business_profile = db.relationship("BusinessProfile", foreign_keys=[business_profile_id], back_populates="instagram_accounts")
    comments = db.relationship("Comment", foreign_keys="Comment.instagram_account_id", back_populates="instagram_account", lazy="dynamic", cascade="all, delete-orphan")
    conversations = db.relationship("Conversation", foreign_keys="Conversation.instagram_account_id", back_populates="instagram_account", lazy="dynamic", cascade="all, delete-orphan")
    
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