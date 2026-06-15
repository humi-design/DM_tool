"""Billing routes for subscription, payment, and usage management."""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from app import db
from models.organization import Organization
from models.subscription import Subscription
from models.plan import Plan, PlanFeature, OrganizationFeature
from models.invoice import Invoice
from models.payment import Payment
from models.usage import UsageRecord, OrganizationUsage
from models.saas import SaaSPlan, SaaSFeature

from billing.services import BillingService, PlanService, UsageService, FeatureService
from billing.constants import get_plans_from_database, get_features_from_database

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


def get_current_organization():
    """Get current user's organization."""
    if hasattr(current_user, 'organization_id'):
        return Organization.query.get(current_user.organization_id)
    if hasattr(current_user, 'organization'):
        return current_user.organization
    return None


def get_billing_service() -> BillingService:
    """Get billing service instance."""
    provider = current_app.config.get("BILLING_PROVIDER", "stripe")
    return BillingService(provider_type=provider)


# ============ Page Routes ============

@billing_bp.route("/")
@login_required
def index():
    """Billing dashboard page."""
    organization = get_current_organization()
    if not organization:
        return redirect(url_for("onboarding.index"))
    
    subscription = Subscription.query.filter_by(
        organization_id=organization.id
    ).order_by(Subscription.created_at.desc()).first()
    
    plan = Plan.get_by_slug(organization.plan) if organization.plan else None
    usage = UsageService.get_usage_summary(organization.id, plan)
    
    # Get recent invoices
    recent_invoices = Invoice.query.filter_by(
        organization_id=organization.id
    ).order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Get recent payments
    recent_payments = Payment.query.filter_by(
        organization_id=organization.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    # Get all plans for comparison
    plans = PlanService.get_plans()
    
    return render_template(
        "billing/index.html",
        organization=organization,
        subscription=subscription,
        plan=plan,
        usage=usage,
        recent_invoices=recent_invoices,
        recent_payments=recent_payments,
        plans=plans
    )


@billing_bp.route("/plans")
def plans():
    """Pricing plans page."""
    current_org = get_current_organization()
    current_plan = current_org.plan if current_org else None
    
    # Get plans from database (dynamic)
    db_plans = get_plans_from_database()
    
    plans_data = []
    for plan in db_plans:
        plans_data.append({
            "name": plan.name,
            "slug": plan.slug,
            "description": plan.description,
            "price_monthly": float(plan.price_monthly),
            "price_annual": float(plan.price_annual),
            "trial_days": plan.trial_days,
            "features": {f.feature.feature_key: f.is_enabled for f in plan.features if f.feature},
            "is_current": current_plan == plan.slug,
            "plan_obj": plan
        })
    
    return render_template(
        "billing/plans.html",
        plans=plans_data,
        current_plan=current_plan
    )


@billing_bp.route("/subscription")
@login_required
def subscription():
    """Current subscription page."""
    organization = get_current_organization()
    if not organization:
        return redirect(url_for("onboarding.index"))
    
    subscription = Subscription.query.filter_by(
        organization_id=organization.id
    ).order_by(Subscription.created_at.desc()).first()
    
    plan = Plan.get_by_slug(organization.plan) if organization.plan else None
    
    # Get subscription history
    subscription_history = Subscription.query.filter_by(
        organization_id=organization.id
    ).order_by(Subscription.created_at.desc()).all()
    
    return render_template(
        "billing/subscription.html",
        organization=organization,
        subscription=subscription,
        plan=plan,
        subscription_history=subscription_history
    )


@billing_bp.route("/invoices")
@login_required
def invoices():
    """Invoices page."""
    organization = get_current_organization()
    if not organization:
        return redirect(url_for("onboarding.index"))
    
    page = request.args.get("page", 1, type=int)
    per_page = 10
    
    invoices_query = Invoice.query.filter_by(
        organization_id=organization.id
    ).order_by(Invoice.created_at.desc())
    
    # Paginate
    total = invoices_query.count()
    invoices_list = invoices_query.offset((page - 1) * per_page).limit(per_page).all()
    
    return render_template(
        "billing/invoices.html",
        organization=organization,
        invoices=invoices_list,
        page=page,
        total_pages=(total + per_page - 1) // per_page,
        total=total
    )


@billing_bp.route("/invoices/<invoice_id>")
@login_required
def invoice_detail(invoice_id):
    """Invoice detail page."""
    organization = get_current_organization()
    if not organization:
        return redirect(url_for("onboarding.index"))
    
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        organization_id=organization.id
    ).first_or_404()
    
    return render_template(
        "billing/invoice_detail.html",
        organization=organization,
        invoice=invoice
    )


@billing_bp.route("/payment-methods", methods=["GET", "POST"])
@login_required
def payment_methods():
    """Payment methods page."""
    organization = get_current_organization()
    if not organization:
        return redirect(url_for("onboarding.index"))
    
    if request.method == "POST":
        # Handle add payment method
        flash("Payment method added successfully", "success")
        return redirect(url_for("billing.payment_methods"))
    
    # Get payment methods from provider
    billing_service = get_billing_service()
    customer_id = organization.metadata_json.get("payment_customer_id")
    
    payment_methods_list = []
    if customer_id:
        try:
            payment_methods_list = billing_service.provider.list_payment_methods(customer_id)
        except Exception as e:
            current_app.logger.error(f"Failed to fetch payment methods: {e}")
    
    return render_template(
        "billing/payment_methods.html",
        organization=organization,
        payment_methods=payment_methods_list
    )


@billing_bp.route("/usage")
@login_required
def usage():
    """Usage tracking page."""
    organization = get_current_organization()
    if not organization:
        return redirect(url_for("onboarding.index"))
    
    plan = Plan.get_by_slug(organization.plan) if organization.plan else None
    usage_summary = UsageService.get_usage_summary(organization.id, plan)
    usage_history = UsageService.get_usage_history(organization.id, days=90)
    
    return render_template(
        "billing/usage.html",
        organization=organization,
        plan=plan,
        usage=usage_summary,
        usage_history=usage_history
    )


@billing_bp.route("/features")
@login_required
def features():
    """Feature management page."""
    organization = get_current_organization()
    if not organization:
        return redirect(url_for("onboarding.index"))
    
    plan = Plan.get_by_slug(organization.plan) if organization.plan else None
    org_features = FeatureService.get_organization_features(organization.id)
    
    # Get all available features from database (dynamic)
    db_features = get_features_from_database()
    
    # Get all available features
    all_features = []
    for feature in db_features:
        org_feature = next(
            (f for f in org_features if f.feature_id == feature.id),
            None
        )
        
        is_enabled = (
            (org_feature.is_enabled if org_feature else False) or
            (plan.has_feature(feature.feature_key) if plan else False)
        )
        
        is_trial = org_feature.is_trial if org_feature else False
        trial_expired = org_feature.is_trial_expired() if org_feature else False
        
        all_features.append({
            "slug": feature.feature_key,
            "name": feature.feature_name,
            "description": feature.description,
            "category": feature.category,
            "icon": feature.icon,
            "is_module": feature.is_module,
            "is_enabled": is_enabled and not (is_trial and trial_expired),
            "is_trial": is_trial,
            "trial_expired": trial_expired,
            "trial_ends_at": org_feature.trial_ends_at if org_feature else None,
        })
    
    # Group by category
    categories = {}
    for feature in all_features:
        cat = feature.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(feature)
    
    return render_template(
        "billing/features.html",
        organization=organization,
        plan=plan,
        features=all_features,
        categories=categories
    )


# ============ API Routes ============

@billing_bp.route("/api/plans", methods=["GET"])
def api_plans():
    """Get all available plans from database (dynamic)."""
    db_plans = get_plans_from_database()
    
    plans_data = []
    for plan in db_plans:
        plans_data.append({
            "id": plan.id,
            "name": plan.name,
            "slug": plan.slug,
            "description": plan.description,
            "price_monthly": float(plan.price_monthly),
            "price_annual": float(plan.price_annual),
            "currency": plan.currency,
            "trial_days": plan.trial_days,
            "features": {f.feature.feature_key: f.is_enabled for f in plan.features if f.feature},
            "limits": plan.get_limit('ai_requests_per_month'),  # Get from plan limits
            "is_featured": plan.is_featured if hasattr(plan, 'is_featured') else False,
        })
    
    return jsonify({"plans": plans_data})


@billing_bp.route("/api/subscription", methods=["GET", "POST"])
@login_required
def api_subscription():
    """Get or create subscription."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    if request.method == "GET":
        subscription = Subscription.query.filter_by(
            organization_id=organization.id
        ).order_by(Subscription.created_at.desc()).first()
        
        if not subscription:
            return jsonify({"subscription": None})
        
        return jsonify({
            "subscription": {
                "id": subscription.id,
                "plan_name": subscription.plan_name,
                "status": subscription.status,
                "billing_cycle": subscription.billing_cycle,
                "current_period_start": subscription.billing_period_start.isoformat() if subscription.billing_period_start else None,
                "current_period_end": subscription.billing_period_end.isoformat() if subscription.billing_period_end else None,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "is_active": subscription.is_active,
            }
        })
    
    # POST - Create subscription
    data = request.get_json()
    plan_slug = data.get("plan_slug")
    billing_cycle = data.get("billing_cycle", "monthly")
    
    plan_def = get_plan_by_slug(plan_slug)
    if not plan_def:
        return jsonify({"error": "Plan not found"}), 400
    
    plan = Plan.get_by_slug(plan_slug)
    if not plan:
        # Create plan if doesn't exist
        plan = PlanService.create_plan(
            name=plan_def["name"],
            slug=plan_def["slug"],
            price_monthly=plan_def["price_monthly"],
            price_annual=plan_def["price_annual"],
            features=plan_def["features"],
            max_users=plan_def["max_users"],
            max_businesses=plan_def["max_businesses"],
            max_api_requests_per_month=plan_def["max_api_requests_per_month"],
            max_ai_requests_per_month=plan_def["max_ai_requests_per_month"],
            max_storage_mb=plan_def["max_storage_mb"],
            trial_days=plan_def["trial_days"],
            sort_order=plan_def["sort_order"],
            is_featured=plan_def.get("is_featured", False),
        )
    
    billing_service = get_billing_service()
    
    try:
        # Create checkout session
        success_url = url_for("billing.subscription", _external=True)
        cancel_url = url_for("billing.plans", _external=True)
        
        checkout_data = billing_service.create_checkout_session(
            organization=organization,
            plan=plan,
            billing_cycle=billing_cycle,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return jsonify({
            "checkout_url": checkout_data.get("url"),
            "checkout_session_id": checkout_data.get("session_id"),
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to create subscription: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/subscription/cancel", methods=["POST"])
@login_required
def api_cancel_subscription():
    """Cancel subscription."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.get_json() or {}
    at_period_end = data.get("at_period_end", True)
    
    subscription = Subscription.query.filter_by(
        organization_id=organization.id
    ).order_by(Subscription.created_at.desc()).first()
    
    if not subscription:
        return jsonify({"error": "No active subscription"}), 400
    
    billing_service = get_billing_service()
    
    try:
        billing_service.cancel_subscription(subscription, at_period_end=at_period_end)
        
        return jsonify({
            "success": True,
            "message": "Subscription canceled" if not at_period_end else "Subscription will be canceled at period end"
        })
        
    except Exception as e:
        current_app.logger.error(f"Failed to cancel subscription: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/subscription/resume", methods=["POST"])
@login_required
def api_resume_subscription():
    """Resume canceled subscription."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    subscription = Subscription.query.filter_by(
        organization_id=organization.id
    ).order_by(Subscription.created_at.desc()).first()
    
    if not subscription:
        return jsonify({"error": "No subscription found"}), 400
    
    if not subscription.cancel_at_period_end:
        return jsonify({"error": "Subscription is not scheduled for cancellation"}), 400
    
    subscription.cancel_at_period_end = False
    db.session.commit()
    
    return jsonify({"success": True, "message": "Subscription resumed"})


@billing_bp.route("/api/subscription/change-plan", methods=["POST"])
@login_required
def api_change_plan():
    """Change subscription plan."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.get_json()
    new_plan_slug = data.get("plan_slug")
    billing_cycle = data.get("billing_cycle")
    
    subscription = Subscription.query.filter_by(
        organization_id=organization.id,
        status=Subscription.STATUS_ACTIVE
    ).first()
    
    if not subscription:
        return jsonify({"error": "No active subscription"}), 400
    
    new_plan_def = get_plan_by_slug(new_plan_slug)
    if not new_plan_def:
        return jsonify({"error": "Plan not found"}), 400
    
    new_plan = Plan.get_by_slug(new_plan_slug)
    
    billing_service = get_billing_service()
    
    try:
        billing_service.change_plan(
            subscription=subscription,
            new_plan=new_plan,
            billing_cycle=billing_cycle
        )
        
        return jsonify({"success": True, "message": "Plan changed successfully"})
        
    except Exception as e:
        current_app.logger.error(f"Failed to change plan: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/invoices", methods=["GET"])
@login_required
def api_invoices():
    """Get invoices."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    invoices_query = Invoice.query.filter_by(
        organization_id=organization.id
    ).order_by(Invoice.created_at.desc())
    
    total = invoices_query.count()
    invoices = invoices_query.offset((page - 1) * per_page).limit(per_page).all()
    
    return jsonify({
        "invoices": [inv.to_dict() for inv in invoices],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    })


@billing_bp.route("/api/invoices/<invoice_id>", methods=["GET"])
@login_required
def api_invoice_detail(invoice_id):
    """Get invoice detail."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        organization_id=organization.id
    ).first()
    
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    
    return jsonify({"invoice": invoice.to_dict(include_organization=True)})


@billing_bp.route("/api/payment-methods", methods=["GET", "POST"])
@login_required
def api_payment_methods():
    """Get or add payment methods."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    billing_service = get_billing_service()
    customer_id = organization.metadata_json.get("payment_customer_id")
    
    if request.method == "GET":
        if not customer_id:
            return jsonify({"payment_methods": []})
        
        try:
            methods = billing_service.provider.list_payment_methods(customer_id)
            return jsonify({
                "payment_methods": [m.__dict__ for m in methods]
            })
        except Exception as e:
            current_app.logger.error(f"Failed to fetch payment methods: {e}")
            return jsonify({"payment_methods": [], "error": str(e)})
    
    # POST - Add payment method
    data = request.get_json()
    payment_method_id = data.get("payment_method_id")
    
    if not customer_id:
        customer_id = billing_service.create_customer(organization)
    
    try:
        billing_service.provider.attach_payment_method(payment_method_id, customer_id)
        billing_service.provider.set_default_payment_method(customer_id, payment_method_id)
        
        return jsonify({"success": True, "message": "Payment method added"})
        
    except Exception as e:
        current_app.logger.error(f"Failed to add payment method: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/payment-methods/<method_id>", methods=["DELETE"])
@login_required
def api_delete_payment_method(method_id):
    """Delete payment method."""
    billing_service = get_billing_service()
    
    try:
        billing_service.provider.detach_payment_method(method_id)
        return jsonify({"success": True, "message": "Payment method removed"})
    except Exception as e:
        current_app.logger.error(f"Failed to delete payment method: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/payment-methods/<method_id>/default", methods=["PUT"])
@login_required
def api_set_default_payment(method_id):
    """Set default payment method."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    customer_id = organization.metadata_json.get("payment_customer_id")
    if not customer_id:
        return jsonify({"error": "Customer not found"}), 404
    
    billing_service = get_billing_service()
    
    try:
        billing_service.provider.set_default_payment_method(customer_id, method_id)
        return jsonify({"success": True, "message": "Default payment method updated"})
    except Exception as e:
        current_app.logger.error(f"Failed to set default payment method: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/usage", methods=["GET"])
@login_required
def api_usage():
    """Get usage data."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    plan = Plan.get_by_slug(organization.plan) if organization.plan else None
    usage_summary = UsageService.get_usage_summary(organization.id, plan)
    
    return jsonify({"usage": usage_summary})


@billing_bp.route("/api/usage/<usage_type>", methods=["POST"])
@login_required
def api_record_usage(usage_type):
    """Record usage."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.get_json() or {}
    count = data.get("count", 1)
    
    subscription = Subscription.query.filter_by(
        organization_id=organization.id,
        status=Subscription.STATUS_ACTIVE
    ).first()
    
    try:
        record = UsageService.record_usage(
            organization_id=organization.id,
            usage_type=usage_type,
            count=count,
            subscription_id=subscription.id if subscription else None
        )
        
        return jsonify({"success": True, "usage_record": record.to_dict()})
    except Exception as e:
        current_app.logger.error(f"Failed to record usage: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/features", methods=["GET"])
@login_required
def api_features():
    """Get organization features."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    features = FeatureService.get_organization_features(organization.id)
    
    return jsonify({
        "features": [f.to_dict() for f in features]
    })


@billing_bp.route("/api/features/<feature_slug>/enable", methods=["POST"])
@login_required
def api_enable_feature(feature_slug):
    """Enable a feature."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.get_json() or {}
    as_trial = data.get("trial", False)
    trial_days = data.get("trial_days", 14)
    
    try:
        feature = FeatureService.enable_feature(
            organization_id=organization.id,
            feature_slug=feature_slug,
            as_trial=as_trial,
            trial_days=trial_days
        )
        
        return jsonify({"success": True, "feature": feature.to_dict()})
    except Exception as e:
        current_app.logger.error(f"Failed to enable feature: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/features/<feature_slug>/disable", methods=["POST"])
@login_required
def api_disable_feature(feature_slug):
    """Disable a feature."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    try:
        FeatureService.disable_feature(
            organization_id=organization.id,
            feature_slug=feature_slug
        )
        
        return jsonify({"success": True})
    except Exception as e:
        current_app.logger.error(f"Failed to disable feature: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route("/api/features/<feature_slug>/trial", methods=["POST"])
@login_required
def api_start_feature_trial(feature_slug):
    """Start trial for a feature."""
    organization = get_current_organization()
    if not organization:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.get_json() or {}
    trial_days = data.get("trial_days", 14)
    
    try:
        feature = FeatureService.start_feature_trial(
            organization_id=organization.id,
            feature_slug=feature_slug,
            trial_days=trial_days
        )
        
        return jsonify({
            "success": True,
            "feature": feature.to_dict(),
            "trial_ends_at": feature.trial_ends_at.isoformat() if feature.trial_ends_at else None
        })
    except Exception as e:
        current_app.logger.error(f"Failed to start feature trial: {e}")
        return jsonify({"error": str(e)}), 500


# ============ Webhook Routes ============

@billing_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhooks."""
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature")
    
    billing_service = get_billing_service()
    
    try:
        billing_service.handle_webhook(payload, signature)
        return jsonify({"received": True})
    except Exception as e:
        current_app.logger.error(f"Stripe webhook error: {e}")
        return jsonify({"error": str(e)}), 400


@billing_bp.route("/webhook/razorpay", methods=["POST"])
def razorpay_webhook():
    """Handle Razorpay webhooks."""
    payload = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature")
    
    billing_service = get_billing_service()
    
    try:
        billing_service.handle_webhook(payload, signature)
        return jsonify({"received": True})
    except Exception as e:
        current_app.logger.error(f"Razorpay webhook error: {e}")
        return jsonify({"error": str(e)}), 400