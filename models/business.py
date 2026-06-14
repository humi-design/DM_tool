"""Business model."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Business(BaseModel, SoftDeleteMixin):
    """Business model for managing business entities."""
    
    __tablename__ = "businesses"
    
    name = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    business_type = db.Column(db.String(100), nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    
    website = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    logo_url = db.Column(db.String(500), nullable=True)
    cover_image_url = db.Column(db.String(500), nullable=True)
    
    settings = db.Column(db.JSON, default=dict, nullable=False)
    metadata = db.Column(db.JSON, default=dict, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    def to_dict(self):
        """Convert business to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        return data


class BusinessProfile(BaseModel):
    """Business profile for Instagram/social media accounts."""
    
    __tablename__ = "business_profiles"
    
    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id"), nullable=False)
    
    platform = db.Column(db.String(50), nullable=False)
    platform_user_id = db.Column(db.String(255), nullable=False)
    platform_username = db.Column(db.String(255), nullable=False)
    platform_profile_url = db.Column(db.String(500), nullable=True)
    platform_avatar_url = db.Column(db.String(500), nullable=True)
    
    access_token = db.Column(db.String(500), nullable=True)
    refresh_token = db.Column(db.String(500), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    
    followers_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    posts_count = db.Column(db.Integer, default=0)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_connected = db.Column(db.Boolean, default=False, nullable=False)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    
    settings = db.Column(db.JSON, default=dict, nullable=False)
    metadata = db.Column(db.JSON, default=dict, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint(
            "business_id", "platform", "platform_user_id",
            name="uq_business_platform_account"
        ),
    )
    
    def to_dict(self, include_tokens: bool = False):
        """Convert business profile to dictionary."""
        data = super().to_dict()
        if not include_tokens:
            data.pop("access_token", None)
            data.pop("refresh_token", None)
        return data