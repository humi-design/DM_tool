"""Plan model for SaaS pricing tiers."""

from datetime import datetime

from app import db
from models.base import BaseModel


class Plan(BaseModel):
    """Pricing plan model."""
    
    __tablename__ = "plans"
    
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Pricing
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False)
    price_annual = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    
    # Limits
    max_users = db.Column(db.Integer, default=1, nullable=False)
    max_api_requests_per_month = db.Column(db.Integer, nullable=True)  # NULL = unlimited
    max_ai_requests_per_month = db.Column(db.Integer, nullable=True)
    max_storage_mb = db.Column(db.Integer, nullable=True)  # NULL = unlimited
    max_businesses = db.Column(db.Integer, default=1, nullable=False)
    
    # Features
    features = db.Column(db.JSON, default=dict, nullable=False)
    
    # Settings
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    trial_days = db.Column(db.Integer, default=0, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    
    # Metadata
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    __table_args__ = (
        db.Index("idx_plan_active_order", "is_active", "sort_order"),
    )
    
    # Plan slugs
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    
    def to_dict(self, include_features: bool = True):
        """Convert plan to dictionary."""
        data = super().to_dict()
        if not include_features:
            data.pop("features", None)
        return data
    
    def has_feature(self, feature: str) -> bool:
        """Check if plan has a specific feature."""
        return self.features.get(feature, False)
    
    def get_feature_value(self, feature: str, default=None):
        """Get feature value or default."""
        return self.features.get(feature, default)
    
    @classmethod
    def get_active_plans(cls):
        """Get all active plans ordered by sort order."""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order).all()
    
    @classmethod
    def get_by_slug(cls, slug: str):
        """Get plan by slug."""
        return cls.query.filter_by(slug=slug, is_active=True).first()
    
    def get_monthly_price(self, billing_cycle: str = "monthly") -> float:
        """Get price based on billing cycle."""
        if billing_cycle == "annual":
            return float(self.price_annual)
        return float(self.price_monthly)
    
    def get_annual_savings(self) -> float:
        """Calculate annual savings compared to monthly billing."""
        monthly_annual = float(self.price_monthly) * 12
        return monthly_annual - float(self.price_annual)


class PlanFeature(BaseModel):
    """Individual features that can be toggled per organization."""
    
    __tablename__ = "plan_features"
    
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    icon = db.Column(db.String(50), nullable=True)
    
    # Display settings
    is_module = db.Column(db.Boolean, default=False, nullable=False)
    is_addon = db.Column(db.Boolean, default=False, nullable=False)
    addon_price_monthly = db.Column(db.Numeric(10, 2), nullable=True)
    addon_price_annual = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Usage tracking
    tracks_usage = db.Column(db.Boolean, default=False, nullable=False)
    usage_unit = db.Column(db.String(50), nullable=True)  # e.g., "requests", "mb", "users"
    usage_included = db.Column(db.Integer, nullable=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    __table_args__ = (
        db.Index("idx_feature_category_active", "category", "is_active"),
    )
    
    # Feature categories
    CATEGORY_AI = "ai"
    CATEGORY_ANALYTICS = "analytics"
    CATEGORY_AUTOMATION = "automation"
    CATEGORY_INTEGRATIONS = "integrations"
    CATEGORY_SUPPORT = "support"
    
    # Feature slugs
    FEATURE_AI_COMMENTS = "ai_comments"
    FEATURE_AI_DM = "ai_dm"
    FEATURE_AI_COACH = "ai_coach"
    FEATURE_LEAD_CAPTURE = "lead_capture"
    FEATURE_REPORTS = "reports"
    FEATURE_DASHBOARD = "dashboard"
    FEATURE_API_ACCESS = "api_access"
    FEATURE_CUSTOM_INTEGRATIONS = "custom_integrations"
    FEATURE_PRIORITY_SUPPORT = "priority_support"
    FEATURE_WHITE_LABEL = "white_label"
    FEATURE_ADVANCED_ANALYTICS = "advanced_analytics"
    FEATURE_A_B_TESTING = "a_b_testing"
    
    def to_dict(self):
        """Convert feature to dictionary."""
        return super().to_dict()
    
    @classmethod
    def get_by_slug(cls, slug: str):
        """Get feature by slug."""
        return cls.query.filter_by(slug=slug, is_active=True).first()
    
    @classmethod
    def get_all_active(cls):
        """Get all active features."""
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_by_category(cls, category: str):
        """Get features by category."""
        return cls.query.filter_by(category=category, is_active=True).all()


class OrganizationFeature(BaseModel):
    """Organization-specific feature flags and add-ons."""
    
    __tablename__ = "organization_features"
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    feature_id = db.Column(
        db.String(36),
        db.ForeignKey("plan_features.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Feature state
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)
    is_trial = db.Column(db.Boolean, default=False, nullable=False)
    trial_ends_at = db.Column(db.DateTime, nullable=True)
    
    # Add-on pricing
    custom_price = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Usage for usage-tracked features
    current_usage = db.Column(db.Integer, default=0, nullable=False)
    usage_limit = db.Column(db.Integer, nullable=True)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", back_populates="organization_features")
    feature = db.relationship("PlanFeature")
    
    __table_args__ = (
        db.UniqueConstraint("organization_id", "feature_id", name="uq_org_feature"),
        db.Index("idx_org_feature_enabled", "organization_id", "is_enabled"),
    )
    
    def to_dict(self):
        """Convert organization feature to dictionary."""
        data = super().to_dict()
        data["feature"] = self.feature.to_dict() if self.feature else None
        return data
    
    def is_trial_expired(self) -> bool:
        """Check if trial has expired."""
        if not self.is_trial or not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at
    
    def is_usage_exceeded(self) -> bool:
        """Check if usage limit exceeded."""
        if self.usage_limit is None:
            return False
        return self.current_usage >= self.usage_limit
    
    def get_usage_percentage(self) -> float:
        """Get usage percentage."""
        if self.usage_limit is None or self.usage_limit == 0:
            return 0.0
        return min(100.0, (self.current_usage / self.usage_limit) * 100)