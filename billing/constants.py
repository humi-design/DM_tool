"""Billing constants and plan definitions."""

from decimal import Decimal

# Plan slugs
PLAN_FREE = "free"
PLAN_STARTER = "starter"
PLAN_GROWTH = "growth"
PLAN_PRO = "pro"
PLAN_ENTERPRISE = "enterprise"

# Feature slugs
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

# Default plan definitions
DEFAULT_PLANS = [
    {
        "name": "Free",
        "slug": PLAN_FREE,
        "description": "Perfect for getting started",
        "price_monthly": Decimal("0"),
        "price_annual": Decimal("0"),
        "trial_days": 0,
        "max_users": 1,
        "max_businesses": 1,
        "max_api_requests_per_month": 100,
        "max_ai_requests_per_month": 10,
        "max_storage_mb": 100,
        "features": {
            FEATURE_DASHBOARD: True,
            FEATURE_LEAD_CAPTURE: True,
            FEATURE_AI_COMMENTS: False,
            FEATURE_AI_DM: False,
            FEATURE_AI_COACH: False,
            FEATURE_REPORTS: False,
            FEATURE_API_ACCESS: False,
            FEATURE_ADVANCED_ANALYTICS: False,
            FEATURE_WHITE_LABEL: False,
            FEATURE_PRIORITY_SUPPORT: False,
            FEATURE_CUSTOM_INTEGRATIONS: False,
        },
        "sort_order": 1,
    },
    {
        "name": "Starter",
        "slug": PLAN_STARTER,
        "description": "For small teams growing their presence",
        "price_monthly": Decimal("29"),
        "price_annual": Decimal("290"),
        "trial_days": 14,
        "max_users": 3,
        "max_businesses": 3,
        "max_api_requests_per_month": 5000,
        "max_ai_requests_per_month": 500,
        "max_storage_mb": 1000,
        "features": {
            FEATURE_DASHBOARD: True,
            FEATURE_LEAD_CAPTURE: True,
            FEATURE_AI_COMMENTS: True,
            FEATURE_AI_DM: False,
            FEATURE_AI_COACH: False,
            FEATURE_REPORTS: True,
            FEATURE_API_ACCESS: False,
            FEATURE_ADVANCED_ANALYTICS: False,
            FEATURE_WHITE_LABEL: False,
            FEATURE_PRIORITY_SUPPORT: False,
            FEATURE_CUSTOM_INTEGRATIONS: False,
        },
        "sort_order": 2,
        "is_featured": False,
    },
    {
        "name": "Growth",
        "slug": PLAN_GROWTH,
        "description": "For growing businesses with advanced needs",
        "price_monthly": Decimal("79"),
        "price_annual": Decimal("790"),
        "trial_days": 14,
        "max_users": 10,
        "max_businesses": 10,
        "max_api_requests_per_month": 25000,
        "max_ai_requests_per_month": 2500,
        "max_storage_mb": 5000,
        "features": {
            FEATURE_DASHBOARD: True,
            FEATURE_LEAD_CAPTURE: True,
            FEATURE_AI_COMMENTS: True,
            FEATURE_AI_DM: True,
            FEATURE_AI_COACH: True,
            FEATURE_REPORTS: True,
            FEATURE_API_ACCESS: True,
            FEATURE_ADVANCED_ANALYTICS: True,
            FEATURE_WHITE_LABEL: False,
            FEATURE_PRIORITY_SUPPORT: False,
            FEATURE_CUSTOM_INTEGRATIONS: False,
        },
        "sort_order": 3,
        "is_featured": True,
    },
    {
        "name": "Pro",
        "slug": PLAN_PRO,
        "description": "For established businesses at scale",
        "price_monthly": Decimal("149"),
        "price_annual": Decimal("1490"),
        "trial_days": 14,
        "max_users": 25,
        "max_businesses": 25,
        "max_api_requests_per_month": 100000,
        "max_ai_requests_per_month": 10000,
        "max_storage_mb": 20000,
        "features": {
            FEATURE_DASHBOARD: True,
            FEATURE_LEAD_CAPTURE: True,
            FEATURE_AI_COMMENTS: True,
            FEATURE_AI_DM: True,
            FEATURE_AI_COACH: True,
            FEATURE_REPORTS: True,
            FEATURE_API_ACCESS: True,
            FEATURE_ADVANCED_ANALYTICS: True,
            FEATURE_WHITE_LABEL: True,
            FEATURE_PRIORITY_SUPPORT: True,
            FEATURE_CUSTOM_INTEGRATIONS: False,
        },
        "sort_order": 4,
    },
    {
        "name": "Enterprise",
        "slug": PLAN_ENTERPRISE,
        "description": "For large organizations with custom needs",
        "price_monthly": Decimal("399"),
        "price_annual": Decimal("3990"),
        "trial_days": 30,
        "max_users": None,  # Unlimited
        "max_businesses": None,  # Unlimited
        "max_api_requests_per_month": None,  # Unlimited
        "max_ai_requests_per_month": None,  # Unlimited
        "max_storage_mb": None,  # Unlimited
        "features": {
            FEATURE_DASHBOARD: True,
            FEATURE_LEAD_CAPTURE: True,
            FEATURE_AI_COMMENTS: True,
            FEATURE_AI_DM: True,
            FEATURE_AI_COACH: True,
            FEATURE_REPORTS: True,
            FEATURE_API_ACCESS: True,
            FEATURE_ADVANCED_ANALYTICS: True,
            FEATURE_WHITE_LABEL: True,
            FEATURE_PRIORITY_SUPPORT: True,
            FEATURE_CUSTOM_INTEGRATIONS: True,
        },
        "sort_order": 5,
    },
]

# Feature definitions
DEFAULT_FEATURES = [
    {
        "slug": FEATURE_AI_COMMENTS,
        "name": "AI Comments",
        "description": "Automatically respond to Instagram comments with AI-powered replies",
        "category": "ai",
        "icon": "sparkles",
        "is_module": True,
    },
    {
        "slug": FEATURE_AI_DM,
        "name": "AI DM",
        "description": "Send automated direct messages to engage with your audience",
        "category": "ai",
        "icon": "chat-bubble-left-right",
        "is_module": True,
    },
    {
        "slug": FEATURE_AI_COACH,
        "name": "AI Coach",
        "description": "Get personalized coaching and recommendations for your content strategy",
        "category": "ai",
        "icon": "academic-cap",
        "is_module": True,
    },
    {
        "slug": FEATURE_LEAD_CAPTURE,
        "name": "Lead Capture",
        "description": "Capture and manage leads from your Instagram interactions",
        "category": "automation",
        "icon": "user-plus",
        "is_module": False,
        "is_addon": False,
    },
    {
        "slug": FEATURE_REPORTS,
        "name": "Reports",
        "description": "Generate comprehensive reports on your Instagram performance",
        "category": "analytics",
        "icon": "chart-bar",
        "is_module": True,
    },
    {
        "slug": FEATURE_DASHBOARD,
        "name": "Dashboard",
        "description": "Access your centralized dashboard with all metrics and insights",
        "category": "analytics",
        "icon": "squares-2x2",
        "is_module": False,
        "is_addon": False,
    },
    {
        "slug": FEATURE_API_ACCESS,
        "name": "API Access",
        "description": "Access our API to build custom integrations and automations",
        "category": "integrations",
        "icon": "code-bracket",
        "is_module": True,
    },
    {
        "slug": FEATURE_ADVANCED_ANALYTICS,
        "name": "Advanced Analytics",
        "description": "Deep dive into your metrics with advanced analytics and trends",
        "category": "analytics",
        "icon": "chart-bar-square",
        "is_module": True,
    },
    {
        "slug": FEATURE_WHITE_LABEL,
        "name": "White Label",
        "description": "Remove branding and use your own branding on reports and emails",
        "category": "integrations",
        "icon": "paint-brush",
        "is_module": True,
    },
    {
        "slug": FEATURE_PRIORITY_SUPPORT,
        "name": "Priority Support",
        "description": "Get priority access to our support team with faster response times",
        "category": "support",
        "icon": "headphones",
        "is_module": False,
        "is_addon": False,
    },
    {
        "slug": FEATURE_CUSTOM_INTEGRATIONS,
        "name": "Custom Integrations",
        "description": "Get custom integration support for your specific tools and workflows",
        "category": "integrations",
        "icon": "puzzle-piece",
        "is_module": True,
    },
]

# Billing cycle constants
BILLING_MONTHLY = "monthly"
BILLING_ANNUAL = "annual"

BILLING_CYCLES = [BILLING_MONTHLY, BILLING_ANNUAL]

# Currency settings
DEFAULT_CURRENCY = "USD"
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "INR", "AUD", "CAD"]

# Usage types
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

# Payment provider settings
PROVIDER_STRIPE = "stripe"
PROVIDER_RAZORPAY = "razorpay"


def get_plan_by_slug(slug: str) -> dict:
    """Get plan definition by slug."""
    for plan in DEFAULT_PLANS:
        if plan["slug"] == slug:
            return plan
    return None


def get_feature_by_slug(slug: str) -> dict:
    """Get feature definition by slug."""
    for feature in DEFAULT_FEATURES:
        if feature["slug"] == slug:
            return feature
    return None


def get_all_plan_slugs() -> list:
    """Get all plan slugs."""
    return [p["slug"] for p in DEFAULT_PLANS]


def get_featured_plan_slug() -> str:
    """Get the featured plan slug."""
    for plan in DEFAULT_PLANS:
        if plan.get("is_featured"):
            return plan["slug"]
    return PLAN_PRO


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