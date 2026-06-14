"""Business model."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Business(BaseModel, SoftDeleteMixin):
    """Business model for managing business entities."""
    
    __tablename__ = "businesses"
    
    name = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    business_type = db.Column(db.String(100), nullable=True, index=True)
    industry = db.Column(db.String(100), nullable=True, index=True)
    
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    website = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True, index=True)
    country = db.Column(db.String(100), nullable=True, index=True)
    
    logo_url = db.Column(db.String(500), nullable=True)
    cover_image_url = db.Column(db.String(500), nullable=True)
    
    settings = db.Column(db.JSON, default=dict, nullable=False)
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    organization = db.relationship("Organization", foreign_keys=[organization_id], back_populates="businesses")
    owner = db.relationship("User", foreign_keys=[owner_id], back_populates="owned_businesses")
    instagram_accounts = db.relationship("InstagramAccount", foreign_keys="InstagramAccount.business_id", back_populates="business", lazy="dynamic", cascade="all, delete-orphan")
    leads = db.relationship("Lead", foreign_keys="Lead.business_id", back_populates="business", lazy="dynamic", cascade="all, delete-orphan")
    comments = db.relationship("Comment", foreign_keys="Comment.business_id", back_populates="business", lazy="dynamic", cascade="all, delete-orphan")
    resources = db.relationship("Resource", foreign_keys="Resource.business_id", back_populates="business", lazy="dynamic", cascade="all, delete-orphan")
    reports = db.relationship("Report", foreign_keys="Report.business_id", back_populates="business", lazy="dynamic", cascade="all, delete-orphan")
    ai_processing_logs = db.relationship("AIProcessingLog", back_populates="business", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.UniqueConstraint("organization_id", "slug", name="uq_business_org_slug"),
        db.Index("idx_business_org_active", "organization_id", "is_active"),
        db.Index("idx_business_type_active", "business_type", "is_active"),
    )
    
    def to_dict(self):
        """Convert business to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data


class BusinessProfile(BaseModel):
    """Business profile for Instagram/social media accounts."""
    
    __tablename__ = "business_profiles"
    
    business_id = db.Column(db.String(36), db.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    platform = db.Column(db.String(50), nullable=False, index=True)
    platform_user_id = db.Column(db.String(255), nullable=False, index=True)
    platform_username = db.Column(db.String(255), nullable=False, index=True)
    platform_profile_url = db.Column(db.String(500), nullable=True)
    platform_avatar_url = db.Column(db.String(500), nullable=True)
    
    access_token = db.Column(db.String(500), nullable=True)
    refresh_token = db.Column(db.String(500), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True, index=True)
    
    followers_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    posts_count = db.Column(db.Integer, default=0)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_connected = db.Column(db.Boolean, default=False, nullable=False, index=True)
    last_synced_at = db.Column(db.DateTime, nullable=True, index=True)
    
    settings = db.Column(db.JSON, default=dict, nullable=False)
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="instagram_accounts")
    instagram_accounts = db.relationship("InstagramAccount", foreign_keys="InstagramAccount.business_profile_id", back_populates="business_profile", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.UniqueConstraint(
            "business_id", "platform", "platform_user_id",
            name="uq_business_platform_account"
        ),
        db.Index("idx_bp_business_platform", "business_id", "platform"),
        db.Index("idx_bp_platform_connected", "platform", "is_connected"),
    )
    
    def to_dict(self, include_tokens: bool = False):
        """Convert business profile to dictionary."""
        data = super().to_dict()
        if not include_tokens:
            data.pop("access_token", None)
            data.pop("refresh_token", None)
        return data