"""Dynamic SaaS Platform Models.

This module contains all models for the fully dynamic, multi-tenant SaaS platform.
All plans, features, limits, providers, and configurations are database-driven.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app import db
from models.base import BaseModel


class SaaSPlan(BaseModel):
    """Dynamic plan model for subscription management."""
    
    __tablename__ = 'saas_plans'
    
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Pricing
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    price_annual = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    billing_cycle = db.Column(db.String(20), nullable=False, default='monthly')
    
    # Plan settings
    trial_days = db.Column(db.Integer, nullable=False, default=0)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    features = db.relationship('SaaSPlanFeature', back_populates='plan', cascade='all, delete-orphan')
    limits = db.relationship('SaaSPlanLimit', back_populates='plan', cascade='all, delete-orphan')
    pricing_cards = db.relationship('SaaSPricingCard', back_populates='plan')
    
    def to_dict(self, include_relations: bool = True) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        data = super().to_dict()
        if include_relations:
            data['features'] = [f.to_dict() for f in self.features]
            data['limits'] = {l.limit_key: l.limit_value for l in self.limits}
        return data
    
    def get_price(self, billing_cycle: str = 'monthly') -> Decimal:
        """Get price based on billing cycle."""
        if billing_cycle == 'annual':
            return self.price_annual
        return self.price_monthly
    
    def get_annual_savings(self) -> Decimal:
        """Calculate annual savings compared to monthly billing."""
        monthly_annual = self.price_monthly * 12
        return monthly_annual - self.price_annual
    
    @classmethod
    def get_default_plan(cls) -> Optional['SaaSPlan']:
        """Get the default plan."""
        return cls.query.filter_by(is_default=True, is_active=True).first()
    
    @classmethod
    def get_active_plans(cls) -> List['SaaSPlan']:
        """Get all active, non-archived plans."""
        return cls.query.filter_by(
            is_active=True, 
            is_archived=False
        ).order_by(cls.sort_order).all()
    
    @classmethod
    def get_by_slug(cls, slug: str) -> Optional['SaaSPlan']:
        """Get plan by slug."""
        return cls.query.filter_by(slug=slug, is_archived=False).first()
    
    def enable_feature(self, feature: 'SaaSFeature') -> None:
        """Enable a feature for this plan."""
        existing = SaaSPlanFeature.query.filter_by(
            plan_id=self.id,
            feature_id=feature.id
        ).first()
        
        if not existing:
            plan_feature = SaaSPlanFeature(
                plan_id=self.id,
                feature_id=feature.id,
                is_enabled=True
            )
            db.session.add(plan_feature)
    
    def disable_feature(self, feature: 'SaaSFeature') -> None:
        """Disable a feature for this plan."""
        existing = SaaSPlanFeature.query.filter_by(
            plan_id=self.id,
            feature_id=feature.id
        ).first()
        
        if existing:
            existing.is_enabled = False
    
    def has_feature(self, feature_key: str) -> bool:
        """Check if plan has a specific feature enabled."""
        for pf in self.features:
            if pf.feature and pf.feature.feature_key == feature_key:
                return pf.is_enabled
        return False
    
    def get_limit(self, limit_key: str) -> Optional[int]:
        """Get a limit value for this plan."""
        for pl in self.limits:
            if pl.limit_key == limit_key:
                return pl.limit_value
        return None


class SaaSFeature(BaseModel):
    """Dynamic feature model."""
    
    __tablename__ = 'saas_features'
    
    feature_name = db.Column(db.String(100), nullable=False)
    feature_key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    icon = db.Column(db.String(50), nullable=True)
    
    # Feature type
    is_module = db.Column(db.Boolean, nullable=False, default=False)
    is_addon = db.Column(db.Boolean, nullable=False, default=False)
    addon_price_monthly = db.Column(db.Numeric(10, 2), nullable=True)
    addon_price_annual = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Usage tracking
    tracks_usage = db.Column(db.Boolean, nullable=False, default=False)
    usage_unit = db.Column(db.String(50), nullable=True)
    usage_included = db.Column(db.Integer, nullable=True)
    
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    plan_features = db.relationship('SaaSPlanFeature', back_populates='feature')
    
    # Feature categories
    CATEGORY_AI = 'ai'
    CATEGORY_ANALYTICS = 'analytics'
    CATEGORY_AUTOMATION = 'automation'
    CATEGORY_INTEGRATIONS = 'integrations'
    CATEGORY_SUPPORT = 'support'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feature to dictionary."""
        return super().to_dict()
    
    @classmethod
    def get_active_features(cls) -> List['SaaSFeature']:
        """Get all active features."""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order).all()
    
    @classmethod
    def get_by_key(cls, feature_key: str) -> Optional['SaaSFeature']:
        """Get feature by key."""
        return cls.query.filter_by(feature_key=feature_key, is_active=True).first()
    
    @classmethod
    def get_by_category(cls, category: str) -> List['SaaSFeature']:
        """Get features by category."""
        return cls.query.filter_by(category=category, is_active=True).order_by(cls.sort_order).all()


class SaaSPlanFeature(BaseModel):
    """Association between plans and features."""
    
    __tablename__ = 'saas_plan_features'
    
    plan_id = db.Column(
        db.String(36),
        db.ForeignKey('saas_plans.id', ondelete='CASCADE'),
        nullable=False
    )
    feature_id = db.Column(
        db.String(36),
        db.ForeignKey('saas_features.id', ondelete='CASCADE'),
        nullable=False
    )
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    
    # Relationships
    plan = db.relationship('SaaSPlan', back_populates='features')
    feature = db.relationship('SaaSFeature', back_populates='plan_features')
    
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'feature_id', name='uq_plan_feature'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if self.feature:
            data['feature'] = self.feature.to_dict()
        return data


class SaaSPlanLimit(BaseModel):
    """Dynamic limits per plan."""
    
    __tablename__ = 'saas_plan_limits'
    
    plan_id = db.Column(
        db.String(36),
        db.ForeignKey('saas_plans.id', ondelete='CASCADE'),
        nullable=False
    )
    limit_key = db.Column(db.String(100), nullable=False, index=True)
    limit_value = db.Column(db.Integer, nullable=False)
    period = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    plan = db.relationship('SaaSPlan', back_populates='limits')
    
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'limit_key', name='uq_plan_limit'),
    )
    
    # Common limit keys
    LIMIT_COMMENTS_PER_MONTH = 'comments_per_month'
    LIMIT_DM_PER_MONTH = 'dm_per_month'
    LIMIT_AI_REQUESTS_PER_MONTH = 'ai_requests_per_month'
    LIMIT_LEAD_LIMIT = 'lead_limit'
    LIMIT_RESOURCE_LIMIT = 'resource_limit'
    LIMIT_TEAM_MEMBERS = 'team_members'
    LIMIT_STORAGE_MB = 'storage_mb'
    LIMIT_REPORTS_PER_MONTH = 'reports_per_month'
    LIMIT_INSTAGRAM_ACCOUNTS = 'instagram_accounts'
    LIMIT_STORY_AUTOMATION = 'story_automation'
    LIMIT_LIVE_AUTOMATION = 'live_automation'
    LIMIT_API_REQUESTS_PER_MONTH = 'api_requests_per_month'
    LIMIT_CONVERSATIONS = 'conversations'
    
    # Limit values
    LIMIT_DISABLED = 0
    LIMIT_UNLIMITED = -1
    
    def is_unlimited(self) -> bool:
        """Check if limit is unlimited."""
        return self.limit_value == self.LIMIT_UNLIMITED
    
    def is_disabled(self) -> bool:
        """Check if limit is disabled (0)."""
        return self.limit_value == self.LIMIT_DISABLED
    
    @classmethod
    def get_limit_key_list(cls) -> List[str]:
        """Get list of all standard limit keys."""
        return [
            cls.LIMIT_COMMENTS_PER_MONTH,
            cls.LIMIT_DM_PER_MONTH,
            cls.LIMIT_AI_REQUESTS_PER_MONTH,
            cls.LIMIT_LEAD_LIMIT,
            cls.LIMIT_RESOURCE_LIMIT,
            cls.LIMIT_TEAM_MEMBERS,
            cls.LIMIT_STORAGE_MB,
            cls.LIMIT_REPORTS_PER_MONTH,
            cls.LIMIT_INSTAGRAM_ACCOUNTS,
            cls.LIMIT_STORY_AUTOMATION,
            cls.LIMIT_LIVE_AUTOMATION,
            cls.LIMIT_API_REQUESTS_PER_MONTH,
            cls.LIMIT_CONVERSATIONS,
        ]


class SaaSOrganizationOverride(BaseModel):
    """Customer-specific limit overrides by SUPER_ADMIN."""
    
    __tablename__ = 'saas_organization_overrides'
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    feature_key = db.Column(db.String(100), nullable=True)
    limit_key = db.Column(db.String(100), nullable=True)
    custom_limit = db.Column(db.Integer, nullable=True)
    custom_value = db.Column(db.String(255), nullable=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    reason = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.String(36),
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Relationships
    organization = db.relationship('Organization', back_populates='saas_overrides')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    __table_args__ = (
        db.Index('idx_override_org_feature', 'organization_id', 'feature_key'),
        db.Index('idx_override_org_limit', 'organization_id', 'limit_key'),
    )
    
    def is_expired(self) -> bool:
        """Check if override has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if override is active (not expired and enabled)."""
        return self.is_enabled and not self.is_expired()
    
    @classmethod
    def get_feature_override(cls, organization_id: str, feature_key: str) -> Optional['SaaSOrganizationOverride']:
        """Get active feature override for organization."""
        override = cls.query.filter_by(
            organization_id=organization_id,
            feature_key=feature_key,
            is_enabled=True
        ).first()
        
        if override and override.is_expired():
            return None
        return override
    
    @classmethod
    def get_limit_override(cls, organization_id: str, limit_key: str) -> Optional['SaaSOrganizationOverride']:
        """Get active limit override for organization."""
        override = cls.query.filter_by(
            organization_id=organization_id,
            limit_key=limit_key,
            is_enabled=True
        ).first()
        
        if override and override.is_expired():
            return None
        return override


class SaaSPricingCard(BaseModel):
    """Customizable pricing page cards."""
    
    __tablename__ = 'saas_pricing_cards'
    
    plan_id = db.Column(
        db.String(36),
        db.ForeignKey('saas_plans.id', ondelete='SET NULL'),
        nullable=True
    )
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    badge = db.Column(db.String(50), nullable=True)
    button_text = db.Column(db.String(50), nullable=False, default='Get Started')
    button_url = db.Column(db.String(255), nullable=True)
    theme = db.Column(db.String(50), nullable=False, default='default')
    features = db.Column(db.JSON, nullable=False, default=list)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_visible = db.Column(db.Boolean, nullable=False, default=True)
    is_highlighted = db.Column(db.Boolean, nullable=False, default=False)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    plan = db.relationship('SaaSPlan', back_populates='pricing_cards')
    
    # Theme options
    THEME_DEFAULT = 'default'
    THEME_DARK = 'dark'
    THEME_LIGHT = 'light'
    THEME_ACCENT = 'accent'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if self.plan:
            data['plan'] = self.plan.to_dict(include_relations=False)
        return data
    
    @classmethod
    def get_visible_cards(cls) -> List['SaaSPricingCard']:
        """Get all visible pricing cards ordered."""
        return cls.query.filter_by(
            is_visible=True
        ).order_by(cls.display_order).all()


class SaaSSystemIntegration(BaseModel):
    """Centralized integration configuration."""
    
    __tablename__ = 'saas_system_integrations'
    
    integration_type = db.Column(db.String(50), nullable=False, index=True)
    integration_key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    
    # Encrypted credentials
    credentials = db.Column(db.Text, nullable=True)
    config = db.Column(db.JSON, nullable=False, default=dict)
    is_encrypted = db.Column(db.Boolean, nullable=False, default=True)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_configured = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(50), nullable=False, default='not_configured')
    last_tested_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Integration types
    TYPE_AI = 'ai'
    TYPE_PAYMENT = 'payment'
    TYPE_OAUTH = 'oauth'
    TYPE_EMAIL = 'email'
    TYPE_STORAGE = 'storage'
    TYPE_OTHER = 'other'
    
    # Status values
    STATUS_NOT_CONFIGURED = 'not_configured'
    STATUS_CONFIGURED = 'configured'
    STATUS_DISABLED = 'disabled'
    STATUS_UNAVAILABLE = 'unavailable'
    STATUS_ERROR = 'error'
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if not include_secrets and self.credentials:
            data['credentials'] = '***ENCRYPTED***'
        return data
    
    @classmethod
    def get_by_key(cls, integration_key: str) -> Optional['SaaSSystemIntegration']:
        """Get integration by key."""
        return cls.query.filter_by(integration_key=integration_key).first()
    
    @classmethod
    def get_by_type(cls, integration_type: str) -> List['SaaSSystemIntegration']:
        """Get integrations by type."""
        return cls.query.filter_by(integration_type=integration_type).all()
    
    @classmethod
    def get_active_by_type(cls, integration_type: str) -> List['SaaSSystemIntegration']:
        """Get active integrations by type."""
        return cls.query.filter_by(
            integration_type=integration_type,
            is_active=True
        ).all()


class SaaSPaymentProvider(BaseModel):
    """Dynamic payment provider configuration."""
    
    __tablename__ = 'saas_payment_providers'
    
    provider_type = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    
    # Encrypted credentials
    credentials = db.Column(db.Text, nullable=True)
    config = db.Column(db.JSON, nullable=False, default=dict)
    is_encrypted = db.Column(db.Boolean, nullable=False, default=True)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_configured = db.Column(db.Boolean, nullable=False, default=False)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(50), nullable=False, default='not_configured')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    
    # Configuration
    webhook_url = db.Column(db.String(255), nullable=True)
    supported_currencies = db.Column(db.JSON, nullable=False, default=list)
    supported_payment_methods = db.Column(db.JSON, nullable=False, default=list)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Provider types
    PROVIDER_STRIPE = 'stripe'
    PROVIDER_RAZORPAY = 'razorpay'
    PROVIDER_PAYTM = 'paytm'
    PROVIDER_PHONEPE = 'phonepe'
    PROVIDER_CASHFREE = 'cashfree'
    PROVIDER_PAYPAL = 'paypal'
    PROVIDER_PADDLE = 'paddle'
    PROVIDER_ADYEN = 'adyen'
    PROVIDER_SQUARE = 'square'
    PROVIDER_WISE = 'wise'
    PROVIDER_AUTHORIZE = 'authorize_net'
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if not include_secrets and self.credentials:
            data['credentials'] = '***ENCRYPTED***'
        return data
    
    @classmethod
    def get_active_providers(cls) -> List['SaaSPaymentProvider']:
        """Get all active payment providers."""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order).all()
    
    @classmethod
    def get_default_provider(cls) -> Optional['SaaSPaymentProvider']:
        """Get the default payment provider."""
        return cls.query.filter_by(is_default=True, is_active=True).first()
    
    @classmethod
    def get_configured_providers(cls) -> List['SaaSPaymentProvider']:
        """Get all configured payment providers."""
        return cls.query.filter_by(
            is_active=True,
            is_configured=True
        ).order_by(cls.sort_order).all()


class SaaSOAuthProvider(BaseModel):
    """Dynamic OAuth provider configuration."""
    
    __tablename__ = 'saas_oauth_providers'
    
    provider_type = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    
    # OAuth credentials
    client_id = db.Column(db.Text, nullable=True)
    client_secret = db.Column(db.Text, nullable=True)
    config = db.Column(db.JSON, nullable=False, default=dict)
    is_encrypted = db.Column(db.Boolean, nullable=False, default=True)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_configured = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(50), nullable=False, default='not_configured')
    
    # OAuth URLs
    scopes = db.Column(db.JSON, nullable=False, default=list)
    authorization_url = db.Column(db.String(255), nullable=True)
    token_url = db.Column(db.String(255), nullable=True)
    userinfo_url = db.Column(db.String(255), nullable=True)
    redirect_urls = db.Column(db.JSON, nullable=False, default=list)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Provider types
    PROVIDER_GOOGLE = 'google'
    PROVIDER_META = 'meta'
    PROVIDER_FACEBOOK = 'facebook'
    PROVIDER_INSTAGRAM = 'instagram'
    PROVIDER_WHATSAPP = 'whatsapp'
    PROVIDER_TELEGRAM = 'telegram'
    PROVIDER_APPLE = 'apple'
    PROVIDER_MICROSOFT = 'microsoft'
    PROVIDER_LINKEDIN = 'linkedin'
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if not include_secrets:
            if self.client_id:
                data['client_id'] = '***SET***' if self.client_id else None
            if self.client_secret:
                data['client_secret'] = '***ENCRYPTED***'
        return data
    
    @classmethod
    def get_active_providers(cls) -> List['SaaSOAuthProvider']:
        """Get all active OAuth providers."""
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_configured_providers(cls) -> List['SaaSOAuthProvider']:
        """Get all configured OAuth providers."""
        return cls.query.filter_by(
            is_active=True,
            is_configured=True
        ).all()
    
    @classmethod
    def get_by_type(cls, provider_type: str) -> Optional['SaaSOAuthProvider']:
        """Get OAuth provider by type."""
        return cls.query.filter_by(provider_type=provider_type, is_active=True).first()


class SaaSAIProvider(BaseModel):
    """Dynamic AI provider configuration."""
    
    __tablename__ = 'saas_ai_providers'
    
    provider_type = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    
    # API configuration
    api_key = db.Column(db.Text, nullable=True)
    base_url = db.Column(db.String(255), nullable=True)
    default_model = db.Column(db.String(100), nullable=True)
    available_models = db.Column(db.JSON, nullable=False, default=list)
    config = db.Column(db.JSON, nullable=False, default=dict)
    is_encrypted = db.Column(db.Boolean, nullable=False, default=True)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_configured = db.Column(db.Boolean, nullable=False, default=False)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(50), nullable=False, default='not_configured')
    priority = db.Column(db.Integer, nullable=False, default=0)
    
    # Settings
    timeout = db.Column(db.Float, nullable=False, default=60.0)
    max_retries = db.Column(db.Integer, nullable=False, default=3)
    rate_limit = db.Column(db.Integer, nullable=True)
    
    # Capabilities
    supports_vision = db.Column(db.Boolean, nullable=False, default=False)
    supports_function_calling = db.Column(db.Boolean, nullable=False, default=False)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Provider types
    PROVIDER_GEMINI = 'gemini'
    PROVIDER_OPENAI = 'openai'
    PROVIDER_CLAUDE = 'claude'
    PROVIDER_OLLAMA = 'ollama'
    PROVIDER_QWEN = 'qwen'
    PROVIDER_LLAMA = 'llama'
    PROVIDER_GEMMA = 'gemma'
    PROVIDER_MISTRAL = 'mistral'
    PROVIDER_DEEPSEEK = 'deepseek'
    PROVIDER_GROK = 'grok'
    PROVIDER_PERPLEXITY = 'perplexity'
    PROVIDER_OPENROUTER = 'openrouter'
    PROVIDER_AZURE_OPENAI = 'azure_openai'
    PROVIDER_META_AI = 'meta_ai'
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if not include_secrets and self.api_key:
            data['api_key'] = '***ENCRYPTED***'
        return data
    
    @classmethod
    def get_active_providers(cls) -> List['SaaSAIProvider']:
        """Get all active AI providers ordered by priority."""
        return cls.query.filter_by(
            is_active=True
        ).order_by(cls.priority).all()
    
    @classmethod
    def get_default_provider(cls) -> Optional['SaaSAIProvider']:
        """Get the default AI provider."""
        return cls.query.filter_by(is_default=True, is_active=True).first()
    
    @classmethod
    def get_configured_providers(cls) -> List['SaaSAIProvider']:
        """Get all configured AI providers."""
        return cls.query.filter_by(
            is_active=True,
            is_configured=True
        ).order_by(cls.priority).all()


class SaaSWebhook(BaseModel):
    """Generic webhook management."""
    
    __tablename__ = 'saas_webhooks'
    
    provider = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(500), nullable=False)
    secret = db.Column(db.Text, nullable=True)
    events = db.Column(db.JSON, nullable=False, default=list)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    headers = db.Column(db.JSON, nullable=False, default=dict)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    deliveries = db.relationship('SaaSWebhookDelivery', back_populates='webhook', cascade='all, delete-orphan')
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if not include_secrets and self.secret:
            data['secret'] = '***SET***'
        return data
    
    @classmethod
    def get_active_webhooks(cls) -> List['SaaSWebhook']:
        """Get all active webhooks."""
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_webhooks_for_event(cls, event_type: str) -> List['SaaSWebhook']:
        """Get webhooks subscribed to a specific event."""
        webhooks = cls.query.filter_by(is_active=True).all()
        return [w for w in webhooks if event_type in w.events or '*' in w.events]


class SaaSWebhookDelivery(BaseModel):
    """Webhook delivery tracking."""
    
    __tablename__ = 'saas_webhook_deliveries'
    
    webhook_id = db.Column(
        db.String(36),
        db.ForeignKey('saas_webhooks.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    event_type = db.Column(db.String(100), nullable=False, index=True)
    event_id = db.Column(db.String(100), nullable=True)
    payload = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending', index=True)
    response_code = db.Column(db.Integer, nullable=True)
    response_body = db.Column(db.Text, nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=5)
    next_retry_at = db.Column(db.DateTime, nullable=True)
    signature_valid = db.Column(db.Boolean, nullable=True)
    is_duplicate = db.Column(db.Boolean, nullable=False, default=False)
    processed_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    webhook = db.relationship('SaaSWebhook', back_populates='deliveries')
    
    # Status values
    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_RETRYING = 'retrying'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = super().to_dict()
        if self.payload:
            data['payload_preview'] = self.payload[:200] + '...' if len(self.payload) > 200 else self.payload
        return data
    
    def can_retry(self) -> bool:
        """Check if delivery can be retried."""
        return self.attempts < self.max_attempts and self.status == self.STATUS_FAILED
    
    def increment_attempt(self) -> None:
        """Increment attempt count and calculate next retry."""
        self.attempts += 1
        if self.can_retry():
            from datetime import timedelta
            self.next_retry_at = datetime.utcnow() + timedelta(minutes=2 ** self.attempts)


class SaaSUsageTracking(BaseModel):
    """Detailed usage metrics tracking."""
    
    __tablename__ = 'saas_usage_tracking'
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    metric_key = db.Column(db.String(100), nullable=False, index=True)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    period_type = db.Column(db.String(20), nullable=False, default='monthly')
    used = db.Column(db.Integer, nullable=False, default=0)
    included = db.Column(db.Integer, nullable=True)
    overage = db.Column(db.Integer, nullable=False, default=0)
    unit_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    overage_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    last_reset_at = db.Column(db.DateTime, nullable=True)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    organization = db.relationship('Organization', back_populates='saas_usage_tracking')
    
    __table_args__ = (
        db.Index('idx_usage_org_metric_period', 'organization_id', 'metric_key', 'period_start'),
    )
    
    # Standard metric keys
    METRIC_AI_REQUESTS = 'ai_requests'
    METRIC_DM_SENT = 'dm_sent'
    METRIC_COMMENTS_PROCESSED = 'comments_processed'
    METRIC_LEADS_CAPTURED = 'leads_captured'
    METRIC_STORAGE_MB = 'storage_mb'
    METRIC_API_REQUESTS = 'api_requests'
    METRIC_REPORTS_GENERATED = 'reports_generated'
    METRIC_CONVERSATIONS = 'conversations'
    
    def increment(self, amount: int = 1) -> None:
        """Increment usage."""
        self.used += amount
        self._calculate_overage()
    
    def _calculate_overage(self) -> None:
        """Calculate overage based on included amount."""
        if self.included and self.used > self.included:
            self.overage = self.used - self.included
            self.overage_cost = Decimal(str(self.overage)) * self.unit_cost
        else:
            self.overage = 0
            self.overage_cost = Decimal('0')
    
    def reset(self) -> None:
        """Reset usage counters."""
        self.used = 0
        self.overage = 0
        self.overage_cost = Decimal('0')
        self.last_reset_at = datetime.utcnow()
    
    @classmethod
    def get_metric_key_list(cls) -> List[str]:
        """Get list of standard metric keys."""
        return [
            cls.METRIC_AI_REQUESTS,
            cls.METRIC_DM_SENT,
            cls.METRIC_COMMENTS_PROCESSED,
            cls.METRIC_LEADS_CAPTURED,
            cls.METRIC_STORAGE_MB,
            cls.METRIC_API_REQUESTS,
            cls.METRIC_REPORTS_GENERATED,
            cls.METRIC_CONVERSATIONS,
        ]
    
    @classmethod
    def get_current_period(cls, organization_id: str, metric_key: str) -> 'SaaSUsageTracking':
        """Get or create current period tracking."""
        now = datetime.utcnow()
        
        # Calculate period boundaries
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = next_month
        
        record = cls.query.filter_by(
            organization_id=organization_id,
            metric_key=metric_key,
            period_start=period_start
        ).first()
        
        if not record:
            record = cls(
                organization_id=organization_id,
                metric_key=metric_key,
                period_start=period_start,
                period_end=period_end,
                period_type='monthly'
            )
            db.session.add(record)
        
        return record


class SaaSInvoice(BaseModel):
    """Enhanced invoice tracking."""
    
    __tablename__ = 'saas_invoices'
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    subscription_id = db.Column(
        db.String(36),
        db.ForeignKey('subscriptions.id', ondelete='SET NULL'),
        nullable=True
    )
    invoice_number = db.Column(db.String(50), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    status = db.Column(db.String(50), nullable=False, default='pending', index=True)
    
    # Payment info
    payment_provider = db.Column(db.String(50), nullable=True)
    payment_transaction_id = db.Column(db.String(255), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    
    # Billing period
    billing_period_start = db.Column(db.DateTime, nullable=True)
    billing_period_end = db.Column(db.DateTime, nullable=True)
    
    # Customer info
    customer_name = db.Column(db.String(255), nullable=True)
    customer_email = db.Column(db.String(255), nullable=True)
    
    # Line items
    line_items = db.Column(db.JSON, nullable=False, default=list)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    organization = db.relationship('Organization', back_populates='saas_invoices')
    subscription = db.relationship('Subscription')
    transactions = db.relationship('SaaSTransaction', back_populates='invoice')
    
    # Status values
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_OVERDUE = 'overdue'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'
    
    @classmethod
    def generate_invoice_number(cls) -> str:
        """Generate a unique invoice number."""
        date = datetime.utcnow().strftime('%Y%m')
        count = cls.query.filter(
            cls.invoice_number.like(f'INV-{date}-%')
        ).count()
        return f'INV-{date}-{str(count + 1).zfill(4)}'
    
    @classmethod
    def get_organization_invoices(cls, organization_id: str) -> List['SaaSInvoice']:
        """Get all invoices for an organization."""
        return cls.query.filter_by(
            organization_id=organization_id
        ).order_by(cls.created_at.desc()).all()


class SaaSTransaction(BaseModel):
    """Payment transaction tracking."""
    
    __tablename__ = 'saas_transactions'
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    invoice_id = db.Column(
        db.String(36),
        db.ForeignKey('saas_invoices.id', ondelete='SET NULL'),
        nullable=True
    )
    provider = db.Column(db.String(50), nullable=False, index=True)
    transaction_id = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    status = db.Column(db.String(50), nullable=False, index=True)
    transaction_type = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    gateway_response = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    
    # Relationships
    organization = db.relationship('Organization', back_populates='saas_transactions')
    invoice = db.relationship('SaaSInvoice', back_populates='transactions')
    
    # Status values
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_DISPUTED = 'disputed'
    
    # Transaction types
    TYPE_PAYMENT = 'payment'
    TYPE_REFUND = 'refund'
    TYPE_CREDIT = 'credit'
    TYPE_CHARGEBACK = 'chargeback'
