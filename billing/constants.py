"""Billing constants and configuration.

This module provides constants and helpers for the billing system.
All plans, features, and configurations are now dynamically loaded from
the database. This file provides only non-database constants.

NOTE: All hardcoded plans have been moved to database tables:
- saas_plans (dynamic plans)
- saas_features (dynamic features)
- saas_plan_features (plan-feature associations)
- saas_plan_limits (plan limits)
- saas_pricing_cards (customizable pricing cards)

Use SaaSPlan, SaaSFeature from models.saas instead of hardcoded constants.
Use FeatureGate from services.feature_gate for permission checking.
"""

from decimal import Decimal


# ===============================================================================
# DEPRECATED: These constants are kept for backward compatibility only.
# Use the database-driven models instead.
# ===============================================================================

# Legacy feature slugs (deprecated - use SaaSFeature model)
FEATURE_AI_COMMENTS = "ai_comments"
FEATURE_AI_DM = "ai_dm"
FEATURE_AI_COACH = "ai_coach"
FEATURE_LEAD_CAPTURE = "lead_capture"
FEATURE_REPORTS = "reports"
FEATURE_DASHBOARD = "dashboard"
FEATURE_API_ACCESS = "api_access"
FEATURE_ADVANCED_ANALYTICS = "advanced_analytics"
FEATURE_WHITE_LABEL = "white_label"
FEATURE_PRIORITY_SUPPORT = "priority_support"
FEATURE_CUSTOM_INTEGRATIONS = "custom_integrations"

# Legacy billing cycle constants
BILLING_MONTHLY = "monthly"
BILLING_ANNUAL = "annual"
BILLING_CYCLES = [BILLING_MONTHLY, BILLING_ANNUAL]

# Currency settings
DEFAULT_CURRENCY = "USD"
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "INR", "AUD", "CAD"]

# Usage types (deprecated - use SaaSUsageTracking model)
USAGE_API_REQUESTS = "api_requests"
USAGE_AI_REQUESTS = "ai_requests"
USAGE_STORAGE_MB = "storage_mb"
USAGE_MESSAGES_SENT = "messages_sent"
USAGE_LEADS_CAPTURED = "leads_captured"
USAGE_COMMENTS_PROCESSED = "comments_processed"
USAGE_DM_SENT = "dm_sent"

USAGE_TYPES = [
    USAGE_API_REQUESTS,
    USAGE_AI_REQUESTS,
    USAGE_STORAGE_MB,
    USAGE_MESSAGES_SENT,
    USAGE_LEADS_CAPTURED,
    USAGE_COMMENTS_PROCESSED,
    USAGE_DM_SENT,
]

# Payment provider types
PROVIDER_STRIPE = "stripe"
PROVIDER_RAZORPAY = "razorpay"
PROVIDER_PAYTM = "paytm"
PROVIDER_PHONEPE = "phonepe"
PROVIDER_PAYPAL = "paypal"


# ===============================================================================
# DEPRECATED FUNCTIONS - Use database models instead
# ===============================================================================

def get_plan_by_slug(slug: str) -> dict:
    """DEPRECATED: Use SaaSPlan.get_by_slug() instead.
    
    Get plan definition by slug from database.
    """
    from models.saas import SaaSPlan
    plan = SaaSPlan.get_by_slug(slug)
    if plan:
        return plan.to_dict(include_relations=False)
    return None


def get_feature_by_slug(slug: str) -> dict:
    """DEPRECATED: Use SaaSFeature.get_by_key() instead.
    
    Get feature definition by slug from database.
    """
    from models.saas import SaaSFeature
    feature = SaaSFeature.get_by_key(slug)
    if feature:
        return feature.to_dict()
    return None


def get_all_plan_slugs() -> list:
    """DEPRECATED: Use SaaSPlan.get_active_plans() instead.
    
    Get all active plan slugs from database.
    """
    from models.saas import SaaSPlan
    return [p.slug for p in SaaSPlan.get_active_plans()]


def get_featured_plan_slug() -> str:
    """DEPRECATED: No longer has a featured plan concept.
    
    Returns the first active plan slug.
    """
    from models.saas import SaaSPlan
    plans = SaaSPlan.get_active_plans()
    return plans[0].slug if plans else None


def format_price(price: Decimal, currency: str = "USD") -> str:
    """Format price for display."""
    if currency == "USD":
        return f"${price:.0f}"
    elif currency == "EUR":
        return f"€{price:.0f}"
    elif currency == "GBP":
        return f"£{price:.0f}"
    elif currency == "INR":
        return f"₹{price:.0f}"
    return f"{price:.2f} {currency}"


def calculate_annual_savings(monthly_price: Decimal) -> Decimal:
    """Calculate annual savings compared to monthly billing."""
    monthly_annual = monthly_price * 12
    annual_price = monthly_price * 10  # 2 months free
    return monthly_annual - annual_price


# ===============================================================================
# Dynamic getters - Use these for database-driven access
# ===============================================================================

def get_plans_from_database():
    """Get all active plans from database."""
    from models.saas import SaaSPlan
    return SaaSPlan.get_active_plans()


def get_features_from_database():
    """Get all active features from database."""
    from models.saas import SaaSFeature
    return SaaSFeature.get_active_features()


def get_plan_features(plan_id: str):
    """Get all features for a plan from database."""
    from models.saas import SaaSPlan
    plan = SaaSPlan.query.get(plan_id)
    if plan:
        return [pf.feature for pf in plan.features if pf.is_enabled]
    return []


def get_plan_limits(plan_id: str):
    """Get all limits for a plan from database."""
    from models.saas import SaaSPlan
    plan = SaaSPlan.query.get(plan_id)
    if plan:
        return {l.limit_key: l.limit_value for l in plan.limits}
    return {}