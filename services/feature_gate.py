"""Feature Gate Engine.

This is the central permission checking system for the dynamic SaaS platform.
Every feature access request follows this flow:

1. Get Organization
2. Get Subscription
3. Get Plan
4. Check Feature Access
5. Check Usage Limits
6. Allow or Deny

This module replaces all hardcoded plan/feature checks with a unified,
database-driven permission system.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from functools import wraps

from app import db
from models.organization import Organization
from models.subscription import Subscription
from models.saas import (
    SaaSPlan,
    SaaSFeature,
    SaaSPlanFeature,
    SaaSPlanLimit,
    SaaSOrganizationOverride,
    SaaSUsageTracking,
)

logger = logging.getLogger(__name__)


class FeatureGateError(Exception):
    """Base exception for feature gate errors."""
    pass


class FeatureNotFoundError(FeatureGateError):
    """Feature not found."""
    pass


class FeatureDisabledError(FeatureGateError):
    """Feature is disabled."""
    pass


class UsageLimitExceededError(FeatureGateError):
    """Usage limit exceeded."""
    def __init__(self, metric_key: str, used: int, limit: int):
        self.metric_key = metric_key
        self.used = used
        self.limit = limit
        super().__init__(
            f"Usage limit exceeded for {metric_key}: {used}/{limit}"
        )


class PlanNotActiveError(FeatureGateError):
    """Plan is not active."""
    pass


class FeatureGate:
    """Central feature gate engine for permission checking."""
    
    def __init__(self, organization: Organization):
        """Initialize the feature gate for an organization.
        
        Args:
            organization: The organization to check permissions for
        """
        self.organization = organization
        self._subscription = None
        self._plan = None
        self._overrides = {}
        self._feature_cache = {}
        self._limit_cache = {}
    
    @property
    def subscription(self) -> Optional[Subscription]:
        """Get the organization's active subscription."""
        if self._subscription is None:
            self._subscription = Subscription.query.filter_by(
                organization_id=self.organization.id,
                status='active'
            ).order_by(Subscription.created_at.desc()).first()
        return self._subscription
    
    @property
    def plan(self) -> Optional[SaaSPlan]:
        """Get the organization's plan."""
        if self._plan is None:
            # Try to get from subscription first
            if self.subscription:
                self._plan = SaaSPlan.query.get(self.subscription.plan_id)
            
            # Fall back to organization.plan slug
            if not self._plan and self.organization.plan:
                self._plan = SaaSPlan.get_by_slug(self.organization.plan)
            
            # Fall back to default plan
            if not self._plan:
                self._plan = SaaSPlan.get_default_plan()
        
        return self._plan
    
    def _load_overrides(self) -> None:
        """Load organization overrides into cache."""
        if not self._overrides:
            overrides = SaaSOrganizationOverride.query.filter_by(
                organization_id=self.organization.id,
                is_enabled=True
            ).all()
            
            for override in overrides:
                if override.feature_key:
                    self._overrides[f"feature:{override.feature_key}"] = override
                if override.limit_key:
                    self._overrides[f"limit:{override.limit_key}"] = override
    
    def has_feature(self, feature_key: str) -> bool:
        """Check if organization has access to a feature.
        
        Flow:
        1. Check organization override (SUPER_ADMIN can override)
        2. Check plan features
        3. Check default plan features
        
        Args:
            feature_key: The feature key to check
            
        Returns:
            True if feature is enabled for the organization
        """
        # Check cache first
        if feature_key in self._feature_cache:
            return self._feature_cache[feature_key]
        
        self._load_overrides()
        
        # Check override first
        override = self._overrides.get(f"feature:{feature_key}")
        if override:
            result = override.is_active()
            self._feature_cache[feature_key] = result
            return result
        
        # Check plan features
        if self.plan:
            for pf in self.plan.features:
                if pf.feature and pf.feature.feature_key == feature_key:
                    result = pf.is_enabled
                    self._feature_cache[feature_key] = result
                    return result
        
        # Check if feature exists and is active (default to disabled)
        feature = SaaSFeature.get_by_key(feature_key)
        if feature and feature.is_active:
            # Feature exists but not in plan - disabled
            self._feature_cache[feature_key] = False
            return False
        
        # Feature doesn't exist - allow (for backward compatibility)
        # This can be changed to False for strict mode
        self._feature_cache[feature_key] = True
        return True
    
    def is_feature_enabled(self, feature_key: str) -> bool:
        """Alias for has_feature."""
        return self.has_feature(feature_key)
    
    def check_feature(self, feature_key: str) -> None:
        """Check if feature is enabled, raise exception if not.
        
        Args:
            feature_key: The feature key to check
            
        Raises:
            FeatureDisabledError: If feature is not enabled
        """
        if not self.has_feature(feature_key):
            raise FeatureDisabledError(f"Feature '{feature_key}' is not available")
    
    def get_limit(self, limit_key: str) -> int:
        """Get the limit value for a key.
        
        Flow:
        1. Check organization override
        2. Check plan limits
        3. Return None (unlimited)
        
        Args:
            limit_key: The limit key to check
            
        Returns:
            The limit value (-1 = unlimited, 0 = disabled, positive = limit)
        """
        # Check cache first
        if limit_key in self._limit_cache:
            return self._limit_cache[limit_key]
        
        self._load_overrides()
        
        # Check override first
        override = self._overrides.get(f"limit:{limit_key}")
        if override and override.is_active():
            result = override.custom_limit if override.custom_limit is not None else -1
            self._limit_cache[limit_key] = result
            return result
        
        # Check plan limits
        if self.plan:
            limit_value = self.plan.get_limit(limit_key)
            if limit_value is not None:
                self._limit_cache[limit_key] = limit_value
                return limit_value
        
        # Default to unlimited
        self._limit_cache[limit_key] = -1
        return -1
    
    def check_limit(self, limit_key: str) -> Tuple[bool, int, int]:
        """Check if within limit for a key.
        
        Args:
            limit_key: The limit key to check
            
        Returns:
            Tuple of (is_allowed, current_usage, limit)
        """
        limit = self.get_limit(limit_key)
        
        if limit == 0:
            return False, 0, 0  # Disabled
        
        # Get current usage
        usage_record = SaaSUsageTracking.get_current_period(
            self.organization.id,
            limit_key
        )
        current_usage = usage_record.used
        
        if limit == -1:
            return True, current_usage, -1  # Unlimited
        
        return current_usage < limit, current_usage, limit
    
    def check_and_increment_usage(
        self,
        metric_key: str,
        amount: int = 1,
        fail_if_exceeded: bool = True
    ) -> Tuple[bool, int, int]:
        """Check and increment usage atomically.
        
        Args:
            metric_key: The metric key to track
            amount: Amount to increment
            fail_if_exceeded: Whether to raise exception if limit exceeded
            
        Returns:
            Tuple of (success, current_usage, limit)
            
        Raises:
            UsageLimitExceededError: If usage limit exceeded and fail_if_exceeded is True
        """
        # First check
        is_allowed, current, limit = self.check_limit(metric_key)
        
        if not is_allowed and limit > 0:
            if fail_if_exceeded:
                raise UsageLimitExceededError(metric_key, current, limit)
            return False, current, limit
        
        # Increment usage
        usage_record = SaaSUsageTracking.get_current_period(
            self.organization.id,
            metric_key
        )
        usage_record.increment(amount)
        db.session.commit()
        
        return True, usage_record.used, limit
    
    def get_all_limits(self) -> Dict[str, int]:
        """Get all limits for the organization.
        
        Returns:
            Dictionary of limit_key -> limit_value
        """
        limits = {}
        
        # Get all standard limit keys
        standard_limits = SaaSPlanLimit.get_limit_key_list()
        
        for limit_key in standard_limits:
            limits[limit_key] = self.get_limit(limit_key)
        
        return limits
    
    def get_all_features(self) -> Dict[str, bool]:
        """Get all features for the organization.
        
        Returns:
            Dictionary of feature_key -> is_enabled
        """
        features = {}
        
        # Get all active features
        all_features = SaaSFeature.get_active_features()
        
        for feature in all_features:
            features[feature.feature_key] = self.has_feature(feature.feature_key)
        
        return features
    
    def get_usage_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get complete usage summary with limits.
        
        Returns:
            Dictionary of metric_key -> {used, limit, percentage}
        """
        summary = {}
        
        metric_keys = SaaSUsageTracking.get_metric_key_list()
        
        for metric_key in metric_keys:
            is_allowed, used, limit = self.check_limit(metric_key)
            
            percentage = 0
            if limit > 0:
                percentage = min(100, (used / limit) * 100) if used > 0 else 0
            
            summary[metric_key] = {
                'used': used,
                'limit': limit,
                'remaining': max(0, limit - used) if limit > 0 else -1,
                'percentage': percentage,
                'is_unlimited': limit == -1,
                'is_disabled': limit == 0,
            }
        
        return summary
    
    def can_access(
        self,
        feature_key: str = None,
        limit_key: str = None,
        check_usage: bool = True
    ) -> bool:
        """Unified access check.
        
        Args:
            feature_key: Optional feature key to check
            limit_key: Optional limit key to check
            check_usage: Whether to check and increment usage
            
        Returns:
            True if access is allowed
        """
        # Check feature first
        if feature_key and not self.has_feature(feature_key):
            return False
        
        # Check limit
        if limit_key:
            is_allowed, _, _ = self.check_limit(limit_key)
            if not is_allowed:
                return False
        
        return True
    
    @classmethod
    def for_organization(cls, organization_id: str) -> 'FeatureGate':
        """Create a feature gate for an organization.
        
        Args:
            organization_id: The organization ID
            
        Returns:
            FeatureGate instance
        """
        organization = Organization.query.get(organization_id)
        if not organization:
            raise ValueError(f"Organization not found: {organization_id}")
        return cls(organization)
    
    @classmethod
    def for_organization_slug(cls, slug: str) -> 'FeatureGate':
        """Create a feature gate for an organization by slug.
        
        Args:
            slug: The organization slug
            
        Returns:
            FeatureGate instance
        """
        organization = Organization.query.filter_by(slug=slug).first()
        if not organization:
            raise ValueError(f"Organization not found: {slug}")
        return cls(organization)


def require_feature(feature_key: str, error_message: str = None):
    """Decorator to require a feature for a route.
    
    Args:
        feature_key: The feature key required
        error_message: Optional custom error message
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g, jsonify
            
            # Get organization from request context
            organization = getattr(g, 'organization', None)
            
            if not organization:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Organization not found'
                }), 401
            
            gate = FeatureGate(organization)
            
            if not gate.has_feature(feature_key):
                return jsonify({
                    'error': 'Feature Disabled',
                    'message': error_message or f"Feature '{feature_key}' is not available on your plan"
                }), 403
            
            # Store gate in context for potential usage tracking
            g.feature_gate = gate
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_plan(plan_slug: str):
    """Decorator to require a specific plan.
    
    Args:
        plan_slug: The plan slug required
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g, jsonify
            
            organization = getattr(g, 'organization', None)
            
            if not organization:
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Organization not found'
                }), 401
            
            gate = FeatureGate(organization)
            
            if not gate.plan or gate.plan.slug != plan_slug:
                return jsonify({
                    'error': 'Plan Required',
                    'message': f"This feature requires the {plan_slug} plan"
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def track_usage(metric_key: str, amount: int = 1):
    """Decorator to track usage for a route.
    
    Args:
        metric_key: The metric key to track
        amount: Amount to increment (can be a function that takes request)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g
            
            gate = getattr(g, 'feature_gate', None)
            
            if gate:
                try:
                    gate.check_and_increment_usage(metric_key, amount)
                except UsageLimitExceededError as e:
                    from flask import jsonify
                    return jsonify({
                        'error': 'Usage Limit Exceeded',
                        'message': str(e),
                        'metric': e.metric_key,
                        'used': e.used,
                        'limit': e.limit
                    }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


class FeatureGateManager:
    """Manager for global feature gate operations."""
    
    @staticmethod
    def initialize_defaults():
        """Initialize default plans and features if they don't exist."""
        
        # Create default features if none exist
        if SaaSFeature.query.count() == 0:
            default_features = [
                {
                    'feature_key': 'ai_dm',
                    'feature_name': 'AI DM',
                    'description': 'Automated direct messaging with AI',
                    'category': 'ai',
                    'icon': 'chat-bubble-left-right',
                    'is_module': True,
                    'tracks_usage': True,
                    'usage_unit': 'messages',
                },
                {
                    'feature_key': 'ai_comments',
                    'feature_name': 'AI Comments',
                    'description': 'AI-powered comment responses',
                    'category': 'ai',
                    'icon': 'sparkles',
                    'is_module': True,
                    'tracks_usage': True,
                    'usage_unit': 'comments',
                },
                {
                    'feature_key': 'story_automation',
                    'feature_name': 'Story Automation',
                    'description': 'Automated story responses',
                    'category': 'automation',
                    'icon': 'clock',
                    'is_module': True,
                    'tracks_usage': True,
                    'usage_unit': 'stories',
                },
                {
                    'feature_key': 'live_automation',
                    'feature_name': 'Live Automation',
                    'description': 'Automated live stream interactions',
                    'category': 'automation',
                    'icon': 'video-camera',
                    'is_module': True,
                    'tracks_usage': True,
                    'usage_unit': 'interactions',
                },
                {
                    'feature_key': 'dashboard',
                    'feature_name': 'Dashboard',
                    'description': 'Access to analytics dashboard',
                    'category': 'analytics',
                    'icon': 'chart-bar',
                    'is_module': False,
                },
                {
                    'feature_key': 'reports',
                    'feature_name': 'Reports',
                    'description': 'Generate and export reports',
                    'category': 'analytics',
                    'icon': 'document-chart-bar',
                    'is_module': True,
                    'tracks_usage': True,
                    'usage_unit': 'reports',
                },
                {
                    'feature_key': 'lead_capture',
                    'feature_name': 'Lead Capture',
                    'description': 'Capture and manage leads',
                    'category': 'automation',
                    'icon': 'user-plus',
                    'is_module': False,
                    'tracks_usage': True,
                    'usage_unit': 'leads',
                },
                {
                    'feature_key': 'conversation_memory',
                    'feature_name': 'Conversation Memory',
                    'description': 'Remember context across conversations',
                    'category': 'ai',
                    'icon': 'academic-cap',
                    'is_module': True,
                },
                {
                    'feature_key': 'human_takeover',
                    'feature_name': 'Human Takeover',
                    'description': 'Seamless handoff to human agents',
                    'category': 'automation',
                    'icon': 'user',
                    'is_module': True,
                },
                {
                    'feature_key': 'resource_sharing',
                    'feature_name': 'Resource Sharing',
                    'description': 'Share resources with contacts',
                    'category': 'automation',
                    'icon': 'share',
                    'is_module': True,
                    'tracks_usage': True,
                    'usage_unit': 'resources',
                },
                {
                    'feature_key': 'ai_coach',
                    'feature_name': 'AI Coach',
                    'description': 'AI-powered content coaching',
                    'category': 'ai',
                    'icon': 'sparkles',
                    'is_module': True,
                },
            ]
            
            for i, feat in enumerate(default_features):
                feature = SaaSFeature(
                    feature_name=feat['feature_name'],
                    feature_key=feat['feature_key'],
                    description=feat.get('description'),
                    category=feat.get('category'),
                    icon=feat.get('icon'),
                    is_module=feat.get('is_module', False),
                    tracks_usage=feat.get('tracks_usage', False),
                    usage_unit=feat.get('usage_unit'),
                    sort_order=i,
                )
                db.session.add(feature)
            
            db.session.commit()
        
        # Create default plans if none exist
        if SaaSPlan.query.count() == 0:
            default_plans = [
                {
                    'name': 'Free',
                    'slug': 'free',
                    'description': 'Perfect for getting started',
                    'price_monthly': 0,
                    'price_annual': 0,
                    'trial_days': 0,
                    'is_default': True,
                    'sort_order': 1,
                },
                {
                    'name': 'Starter',
                    'slug': 'starter',
                    'description': 'For small teams growing their presence',
                    'price_monthly': 29,
                    'price_annual': 290,
                    'trial_days': 14,
                    'sort_order': 2,
                },
                {
                    'name': 'Growth',
                    'slug': 'growth',
                    'description': 'For growing businesses with advanced needs',
                    'price_monthly': 79,
                    'price_annual': 790,
                    'trial_days': 14,
                    'is_featured': True,
                    'sort_order': 3,
                },
                {
                    'name': 'Pro',
                    'slug': 'pro',
                    'description': 'For established businesses at scale',
                    'price_monthly': 149,
                    'price_annual': 1490,
                    'trial_days': 14,
                    'sort_order': 4,
                },
                {
                    'name': 'Enterprise',
                    'slug': 'enterprise',
                    'description': 'For large organizations with custom needs',
                    'price_monthly': 399,
                    'price_annual': 3990,
                    'trial_days': 30,
                    'sort_order': 5,
                },
            ]
            
            import uuid
            for plan_data in default_plans:
                plan = SaaSPlan(
                    id=str(uuid.uuid4()),
                    name=plan_data['name'],
                    slug=plan_data['slug'],
                    description=plan_data.get('description'),
                    price_monthly=plan_data['price_monthly'],
                    price_annual=plan_data['price_annual'],
                    trial_days=plan_data.get('trial_days', 0),
                    is_default=plan_data.get('is_default', False),
                    sort_order=plan_data.get('sort_order', 0),
                )
                db.session.add(plan)
            
            db.session.commit()
            
            # Assign features to plans
            FeatureGateManager._assign_default_features()
    
    @staticmethod
    def _assign_default_features():
        """Assign features to default plans."""
        plans = SaaSPlan.get_active_plans()
        features = {f.feature_key: f for f in SaaSFeature.get_active_features()}
        
        # Free plan features
        free_plan = SaaSPlan.get_by_slug('free')
        if free_plan:
            # Only basic features
            for key in ['dashboard', 'lead_capture']:
                if key in features:
                    free_plan.enable_feature(features[key])
        
        # Starter plan
        starter_plan = SaaSPlan.get_by_slug('starter')
        if starter_plan:
            for key in ['dashboard', 'lead_capture', 'ai_comments', 'reports']:
                if key in features:
                    starter_plan.enable_feature(features[key])
        
        # Growth plan
        growth_plan = SaaSPlan.get_by_slug('growth')
        if growth_plan:
            for key in features:
                if key in ['dashboard', 'lead_capture', 'ai_comments', 'ai_dm', 
                          'story_automation', 'reports', 'ai_coach']:
                    growth_plan.enable_feature(features[key])
        
        # Pro plan
        pro_plan = SaaSPlan.get_by_slug('pro')
        if pro_plan:
            for key in features:
                if key != 'human_takeover':  # Enterprise only
                    pro_plan.enable_feature(features[key])
        
        # Enterprise plan - all features
        enterprise_plan = SaaSPlan.get_by_slug('enterprise')
        if enterprise_plan:
            for key in features:
                enterprise_plan.enable_feature(features[key])
        
        db.session.commit()
        
        # Set default limits
        FeatureGateManager._assign_default_limits()
    
    @staticmethod
    def _assign_default_limits():
        """Assign default limits to plans."""
        plans = SaaSPlan.get_active_plans()
        
        for plan in plans:
            if plan.slug == 'free':
                limits = {
                    'ai_requests_per_month': 10,
                    'dm_per_month': 50,
                    'comments_per_month': 100,
                    'leads_per_month': 25,
                    'storage_mb': 100,
                    'team_members': 1,
                }
            elif plan.slug == 'starter':
                limits = {
                    'ai_requests_per_month': 500,
                    'dm_per_month': 1000,
                    'comments_per_month': 2000,
                    'leads_per_month': 100,
                    'storage_mb': 1000,
                    'team_members': 3,
                }
            elif plan.slug == 'growth':
                limits = {
                    'ai_requests_per_month': 2500,
                    'dm_per_month': 5000,
                    'comments_per_month': 10000,
                    'leads_per_month': 500,
                    'storage_mb': 5000,
                    'team_members': 10,
                    'instagram_accounts': 3,
                }
            elif plan.slug == 'pro':
                limits = {
                    'ai_requests_per_month': 10000,
                    'dm_per_month': 20000,
                    'comments_per_month': 50000,
                    'leads_per_month': 2000,
                    'storage_mb': 20000,
                    'team_members': 25,
                    'instagram_accounts': 10,
                    'reports_per_month': 100,
                }
            elif plan.slug == 'enterprise':
                limits = {
                    'ai_requests_per_month': -1,  # Unlimited
                    'dm_per_month': -1,
                    'comments_per_month': -1,
                    'leads_per_month': -1,
                    'storage_mb': -1,
                    'team_members': -1,
                    'instagram_accounts': -1,
                    'reports_per_month': -1,
                }
            
            for limit_key, limit_value in limits.items():
                existing = SaaSPlanLimit.query.filter_by(
                    plan_id=plan.id,
                    limit_key=limit_key
                ).first()
                
                if not existing:
                    plan_limit = SaaSPlanLimit(
                        plan_id=plan.id,
                        limit_key=limit_key,
                        limit_value=limit_value,
                        period='monthly'
                    )
                    db.session.add(plan_limit)
        
        db.session.commit()
