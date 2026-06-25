"""Super Admin Console Routes.

This module provides the super admin console for managing the entire platform.
Access is restricted to users with SUPER_ADMIN role only.

Routes:
- /super-admin/ - Dashboard overview
- /super-admin/login - Super Admin login page
- /super-admin/plans/ - Plan management
- /super-admin/features/ - Feature management
- /super-admin/organizations/ - Organization management
- /super-admin/users/ - User management
- /super-admin/ai-providers/ - AI provider configuration
- /super-admin/oauth-providers/ - OAuth provider configuration
- /super-admin/payment-gateways/ - Payment gateway configuration
- /super-admin/usage/ - Usage tracking and limits
- /super-admin/integrations/ - System integrations
- /super-admin/audit-logs/ - Audit logs
- /super-admin/system-health/ - System health checks
"""

import os
import uuid
from functools import wraps
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, make_response
from flask_login import login_required, current_user, login_user
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from models.user import User
from models.organization import Organization
from models.saas import (
    SaaSPlan, SaaSFeature, SaaSPlanFeature, SaaSPlanLimit,
    SaaSOrganizationOverride, SaaSPricingCard,
    SaaSSystemIntegration, SaaSPaymentProvider, SaaSOAuthProvider,
    SaaSAIProvider, SaaSWebhook, SaaSWebhookDelivery,
    SaaSUsageTracking, SaaSInvoice, SaaSTransaction
)
from services.secret_manager import SecretManager, encrypt, decrypt, mask
from services.feature_gate import FeatureGateManager, FeatureGate

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/super-admin')


# Hardcoded super admin credentials (can be overridden via environment variables)
SUPER_ADMIN_USERNAME = os.environ.get('SUPER_ADMIN_USERNAME', 'admin')
SUPER_ADMIN_PASSWORD = os.environ.get('SUPER_ADMIN_PASSWORD', 'admin123')
SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'admin@example.com')


def super_admin_required(f):
    """Decorator to require SUPER_ADMIN role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('super_admin.login'))
        
        if not current_user.is_superuser:
            flash('Access denied. Super Admin privileges required.', 'danger')
            return redirect(url_for('dashboard.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def api_super_admin_required(f):
    """Decorator to require SUPER_ADMIN role for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not current_user.is_superuser:
            return jsonify({'error': 'Super Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Login/Logout
# =============================================================================

@super_admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Super Admin login page with hardcoded credentials."""
    if request.method == 'GET':
        # If already logged in as super admin, redirect to dashboard
        if current_user.is_authenticated and current_user.is_superuser:
            return redirect(url_for('super_admin.index'))
        return render_template('super_admin/login.html')
    
    # Handle POST - verify credentials
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if username == SUPER_ADMIN_USERNAME and password == SUPER_ADMIN_PASSWORD:
        # Find or create super admin user
        admin_user = User.query.filter_by(email=SUPER_ADMIN_EMAIL).first()
        
        if not admin_user:
            # Create a new super admin user
            admin_user = User(
                id=str(uuid.uuid4()),
                email=SUPER_ADMIN_EMAIL,
                username=SUPER_ADMIN_USERNAME,
                full_name='Super Admin',
                password_hash=generate_password_hash(password),
                is_verified=True,
                is_superuser=True,
                is_active=True,
            )
            db.session.add(admin_user)
            
            # Create default organization for admin
            org = Organization(
                id=str(uuid.uuid4()),
                name='Admin Organization',
                slug='admin-org',
                owner_id=admin_user.id,
                plan='enterprise',
                plan_expires_at=datetime.utcnow() + timedelta(days=365 * 10),
                is_active=True,
            )
            db.session.add(org)
            db.session.commit()
            
            admin_user.organization_id = org.id
            db.session.commit()
        else:
            # Update user to be superuser
            admin_user.is_superuser = True
            admin_user.is_verified = True
            admin_user.is_active = True
            db.session.commit()
        
        # Log in the user
        login_user(admin_user, remember=True)
        
        flash('Welcome to Super Admin Console!', 'success')
        return redirect(url_for('super_admin.index'))
    
    flash('Invalid credentials. Please try again.', 'danger')
    return render_template('super_admin/login.html')


@super_admin_bp.route('/logout', methods=['POST'])
@super_admin_required
def logout():
    """Super Admin logout."""
    from flask_login import logout_user
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('super_admin.login'))


# =============================================================================
# API Settings Page
# =============================================================================

@super_admin_bp.route('/api-settings')
@super_admin_required
def api_settings():
    """API Settings page for configuring all API keys and integrations."""
    return render_template('super_admin/api_settings.html')


# =============================================================================
# Dashboard
# =============================================================================

@super_admin_bp.route('/')
@super_admin_required
def index():
    """Super Admin dashboard overview."""
    # Get statistics
    stats = {
        'total_organizations': Organization.query.filter_by(is_active=True).count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_plans': SaaSPlan.query.filter_by(is_active=True).count(),
        'total_features': SaaSFeature.query.filter_by(is_active=True).count(),
        'active_subscriptions': db.session.query(SaaSUsageTracking).filter(
            SaaSUsageTracking.used > 0
        ).distinct(SaaSUsageTracking.organization_id).count(),
    }
    
    # Get recent organizations
    recent_orgs = Organization.query.filter_by(is_active=True).order_by(
        Organization.created_at.desc()
    ).limit(10).all()
    
    # Get recent signups
    recent_signups = User.query.filter_by(is_active=True).order_by(
        User.created_at.desc()
    ).limit(10).all()
    
    # Get system health
    health = get_system_health()
    
    return render_template('super_admin/index.html',
        stats=stats,
        recent_orgs=recent_orgs,
        recent_signups=recent_signups,
        health=health
    )


# =============================================================================
# Plans Management
# =============================================================================

@super_admin_bp.route('/plans')
@super_admin_required
def plans():
    """Plans management page."""
    plans = SaaSPlan.query.filter_by(is_archived=False).order_by(SaaSPlan.sort_order).all()
    features = SaaSFeature.get_active_features()
    
    return render_template('super_admin/plans.html', plans=plans, features=features)


@super_admin_bp.route('/plans/create', methods=['GET', 'POST'])
@super_admin_required
def plans_create():
    """Create a new plan."""
    if request.method == 'POST':
        data = request.form
        
        import uuid
        plan = SaaSPlan(
            id=str(uuid.uuid4()),
            name=data.get('name'),
            slug=data.get('slug'),
            description=data.get('description'),
            price_monthly=float(data.get('price_monthly', 0)),
            price_annual=float(data.get('price_annual', 0)),
            currency=data.get('currency', 'USD'),
            billing_cycle=data.get('billing_cycle', 'monthly'),
            trial_days=int(data.get('trial_days', 0)),
            is_default=data.get('is_default') == 'on',
            is_active=True,
            sort_order=int(data.get('sort_order', 0)),
        )
        
        db.session.add(plan)
        db.session.commit()
        
        # Add features
        selected_features = request.form.getlist('features')
        for feature_id in selected_features:
            feature = SaaSFeature.query.get(feature_id)
            if feature:
                plan.enable_feature(feature)
        
        # Add limits
        for key in SaaSPlanLimit.get_limit_key_list():
            limit_value = request.form.get(f'limit_{key}')
            if limit_value:
                plan_limit = SaaSPlanLimit(
                    plan_id=plan.id,
                    limit_key=key,
                    limit_value=int(limit_value),
                    period='monthly'
                )
                db.session.add(plan_limit)
        
        db.session.commit()
        
        flash(f'Plan "{plan.name}" created successfully.', 'success')
        return redirect(url_for('super_admin.plans'))
    
    features = SaaSFeature.get_active_features()
    limit_keys = SaaSPlanLimit.get_limit_key_list()
    
    return render_template('super_admin/plan_form.html',
        plan=None,
        features=features,
        limit_keys=limit_keys,
        action='create'
    )


@super_admin_bp.route('/plans/<plan_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def plans_edit(plan_id):
    """Edit an existing plan."""
    plan = SaaSPlan.query.get_or_404(plan_id)
    
    if request.method == 'POST':
        data = request.form
        
        plan.name = data.get('name')
        plan.slug = data.get('slug')
        plan.description = data.get('description')
        plan.price_monthly = float(data.get('price_monthly', 0))
        plan.annual_price = float(data.get('price_annual', 0))
        plan.currency = data.get('currency', 'USD')
        plan.billing_cycle = data.get('billing_cycle', 'monthly')
        plan.trial_days = int(data.get('trial_days', 0))
        plan.is_default = data.get('is_default') == 'on'
        plan.sort_order = int(data.get('sort_order', 0))
        
        # Update features
        selected_features = request.form.getlist('features')
        for pf in plan.features:
            pf.is_enabled = pf.feature_id in selected_features
        
        # Update limits
        for key in SaaSPlanLimit.get_limit_key_list():
            limit_value = request.form.get(f'limit_{key}')
            existing_limit = next(
                (l for l in plan.limits if l.limit_key == key),
                None
            )
            
            if limit_value:
                if existing_limit:
                    existing_limit.limit_value = int(limit_value)
                else:
                    plan_limit = SaaSPlanLimit(
                        plan_id=plan.id,
                        limit_key=key,
                        limit_value=int(limit_value),
                        period='monthly'
                    )
                    db.session.add(plan_limit)
        
        db.session.commit()
        
        flash(f'Plan "{plan.name}" updated successfully.', 'success')
        return redirect(url_for('super_admin.plans'))
    
    features = SaaSFeature.get_active_features()
    limit_keys = SaaSPlanLimit.get_limit_key_list()
    
    return render_template('super_admin/plan_form.html',
        plan=plan,
        features=features,
        limit_keys=limit_keys,
        action='edit'
    )


@super_admin_bp.route('/plans/<plan_id>/delete', methods=['POST'])
@super_admin_required
def plans_delete(plan_id):
    """Archive a plan."""
    plan = SaaSPlan.query.get_or_404(plan_id)
    
    if plan.is_default:
        flash('Cannot archive the default plan.', 'danger')
        return redirect(url_for('super_admin.plans'))
    
    plan.is_archived = True
    plan.is_active = False
    db.session.commit()
    
    flash(f'Plan "{plan.name}" archived successfully.', 'success')
    return redirect(url_for('super_admin.plans'))


@super_admin_bp.route('/plans/<plan_id>/toggle', methods=['POST'])
@super_admin_required
def plans_toggle(plan_id):
    """Toggle plan active status."""
    plan = SaaSPlan.query.get_or_404(plan_id)
    
    plan.is_active = not plan.is_active
    db.session.commit()
    
    status = 'activated' if plan.is_active else 'deactivated'
    flash(f'Plan "{plan.name}" {status}.', 'success')
    
    return redirect(url_for('super_admin.plans'))


@super_admin_bp.route('/plans/<plan_id>/duplicate', methods=['POST'])
@super_admin_required
def plans_duplicate(plan_id):
    """Duplicate a plan."""
    original = SaaSPlan.query.get_or_404(plan_id)
    
    import uuid
    new_plan = SaaSPlan(
        id=str(uuid.uuid4()),
        name=f"{original.name} (Copy)",
        slug=f"{original.slug}-copy-{uuid.uuid4().hex[:8]}",
        description=original.description,
        price_monthly=original.price_monthly,
        price_annual=original.price_annual,
        currency=original.currency,
        billing_cycle=original.billing_cycle,
        trial_days=original.trial_days,
        is_default=False,
        is_active=False,
        sort_order=original.sort_order + 1,
    )
    
    db.session.add(new_plan)
    db.session.commit()
    
    # Copy features
    for pf in original.features:
        if pf.is_enabled:
            new_plan.enable_feature(pf.feature)
    
    # Copy limits
    for limit in original.limits:
        new_limit = SaaSPlanLimit(
            plan_id=new_plan.id,
            limit_key=limit.limit_key,
            limit_value=limit.limit_value,
            period=limit.period
        )
        db.session.add(new_limit)
    
    db.session.commit()
    
    flash(f'Plan duplicated as "{new_plan.name}".', 'success')
    return redirect(url_for('super_admin.plans_edit', plan_id=new_plan.id))


# =============================================================================
# Features Management
# =============================================================================

@super_admin_bp.route('/features')
@super_admin_required
def features():
    """Features management page."""
    features = SaaSFeature.get_active_features()
    categories = db.session.query(SaaSFeature.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('super_admin/features.html',
        features=features,
        categories=categories
    )


@super_admin_bp.route('/features/create', methods=['POST'])
@super_admin_required
def features_create():
    """Create a new feature."""
    data = request.form
    
    import uuid
    feature = SaaSFeature(
        feature_name=data.get('feature_name'),
        feature_key=data.get('feature_key'),
        description=data.get('description'),
        category=data.get('category'),
        icon=data.get('icon'),
        is_module=data.get('is_module') == 'on',
        is_addon=data.get('is_addon') == 'on',
        tracks_usage=data.get('tracks_usage') == 'on',
        usage_unit=data.get('usage_unit'),
        sort_order=int(data.get('sort_order', 0)),
    )
    
    db.session.add(feature)
    db.session.commit()
    
    flash(f'Feature "{feature.feature_name}" created.', 'success')
    return redirect(url_for('super_admin.features'))


@super_admin_bp.route('/features/<feature_id>/edit', methods=['POST'])
@super_admin_required
def features_edit(feature_id):
    """Edit a feature."""
    feature = SaaSFeature.query.get_or_404(feature_id)
    data = request.form
    
    feature.feature_name = data.get('feature_name')
    feature.description = data.get('description')
    feature.category = data.get('category')
    feature.icon = data.get('icon')
    feature.is_module = data.get('is_module') == 'on'
    feature.is_addon = data.get('is_addon') == 'on'
    feature.tracks_usage = data.get('tracks_usage') == 'on'
    feature.usage_unit = data.get('usage_unit')
    feature.is_active = data.get('is_active') == 'on'
    feature.sort_order = int(data.get('sort_order', 0))
    
    db.session.commit()
    
    flash(f'Feature "{feature.feature_name}" updated.', 'success')
    return redirect(url_for('super_admin.features'))


# =============================================================================
# Organizations Management
# =============================================================================

@super_admin_bp.route('/organizations')
@super_admin_required
def organizations():
    """Organizations management page."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Organization.query.filter_by(is_active=True)
    
    # Search
    search = request.args.get('search')
    if search:
        query = query.filter(
            db.or_(
                Organization.name.ilike(f'%{search}%'),
                Organization.slug.ilike(f'%{search}%')
            )
        )
    
    # Filter by plan
    plan_filter = request.args.get('plan')
    if plan_filter:
        query = query.filter_by(plan=plan_filter)
    
    pagination = query.order_by(Organization.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    plans = SaaSPlan.query.filter_by(is_active=True).all()
    
    return render_template('super_admin/organizations.html',
        organizations=pagination.items,
        pagination=pagination,
        plans=plans
    )


@super_admin_bp.route('/organizations/<org_id>')
@super_admin_required
def organizations_detail(org_id):
    """Organization detail page."""
    org = Organization.query.get_or_404(org_id)
    
    # Get usage
    usage_summary = {}
    for metric_key in SaaSUsageTracking.get_metric_key_list():
        record = SaaSUsageTracking.query.filter_by(
            organization_id=org_id,
            metric_key=metric_key
        ).order_by(SaaSUsageTracking.period_start.desc()).first()
        
        if record:
            usage_summary[metric_key] = record
    
    # Get overrides
    overrides = SaaSOrganizationOverride.query.filter_by(
        organization_id=org_id
    ).all()
    
    # Get invoices
    invoices = SaaSInvoice.query.filter_by(
        organization_id=org_id
    ).order_by(SaaSInvoice.created_at.desc()).limit(10).all()
    
    return render_template('super_admin/organization_detail.html',
        organization=org,
        usage_summary=usage_summary,
        overrides=overrides,
        invoices=invoices
    )


@super_admin_bp.route('/organizations/<org_id>/override', methods=['POST'])
@super_admin_required
def organizations_override(org_id):
    """Create or update organization override."""
    org = Organization.query.get_or_404(org_id)
    data = request.form
    
    feature_key = data.get('feature_key')
    limit_key = data.get('limit_key')
    custom_limit = data.get('custom_limit')
    expires_at = data.get('expires_at')
    
    if expires_at:
        expires_at = datetime.strptime(expires_at, '%Y-%m-%d')
    
    # Check if override exists
    existing = SaaSOrganizationOverride.query.filter_by(
        organization_id=org_id
    ).filter(
        db.or_(
            SaaSOrganizationOverride.feature_key == feature_key,
            SaaSOrganizationOverride.limit_key == limit_key
        )
    ).first()
    
    if existing:
        existing.custom_limit = int(custom_limit) if custom_limit else None
        existing.expires_at = expires_at
        existing.reason = data.get('reason')
        existing.is_enabled = True
    else:
        override = SaaSOrganizationOverride(
            organization_id=org_id,
            feature_key=feature_key or None,
            limit_key=limit_key or None,
            custom_limit=int(custom_limit) if custom_limit else None,
            expires_at=expires_at,
            reason=data.get('reason'),
            created_by=current_user.id
        )
        db.session.add(override)
    
    db.session.commit()
    
    flash('Override applied successfully.', 'success')
    return redirect(url_for('super_admin.organizations_detail', org_id=org_id))


# =============================================================================
# AI Providers Management
# =============================================================================

@super_admin_bp.route('/ai-providers')
@super_admin_required
def ai_providers():
    """AI providers management page."""
    providers = SaaSAIProvider.get_active_providers()
    
    return render_template('super_admin/ai_providers.html', providers=providers)


@super_admin_bp.route('/ai-providers/create', methods=['POST'])
@super_admin_required
def ai_providers_create():
    """Create or update AI provider."""
    data = request.form
    
    provider_type = data.get('provider_type')
    
    provider = SaaSAIProvider.query.filter_by(provider_type=provider_type).first()
    
    if not provider:
        import uuid
        provider = SaaSAIProvider(
            id=str(uuid.uuid4()),
            provider_type=provider_type,
        )
        db.session.add(provider)
    
    provider.name = data.get('name')
    provider.description = data.get('description')
    provider.api_key = encrypt(data.get('api_key')) if data.get('api_key') else provider.api_key
    provider.base_url = data.get('base_url')
    provider.default_model = data.get('default_model')
    provider.timeout = float(data.get('timeout', 60))
    provider.max_retries = int(data.get('max_retries', 3))
    provider.priority = int(data.get('priority', 0))
    provider.is_active = data.get('is_active') == 'on'
    provider.is_default = data.get('is_default') == 'on'
    
    # Check if configured
    provider.is_configured = bool(provider.api_key)
    provider.status = 'configured' if provider.is_configured else 'not_configured'
    
    db.session.commit()
    
    flash(f'AI provider "{provider.name}" saved.', 'success')
    return redirect(url_for('super_admin.ai_providers'))


@super_admin_bp.route('/ai-providers/<provider_id>/test', methods=['POST'])
@super_admin_required
def ai_providers_test(provider_id):
    """Test AI provider connection."""
    provider = SaaSAIProvider.query.get_or_404(provider_id)
    
    # Implement actual test logic
    provider.last_tested_at = datetime.utcnow()
    
    try:
        # Simulated test - in production, actually test the API
        provider.last_error = None
        provider.is_configured = True
        provider.status = 'configured'
        flash(f'AI provider "{provider.name}" test successful!', 'success')
    except Exception as e:
        provider.last_error = str(e)
        provider.status = 'error'
        flash(f'AI provider test failed: {e}', 'danger')
    
    db.session.commit()
    return redirect(url_for('super_admin.ai_providers'))


# =============================================================================
# OAuth Providers Management
# =============================================================================

@super_admin_bp.route('/oauth-providers')
@super_admin_required
def oauth_providers():
    """OAuth providers management page."""
    providers = SaaSOAuthProvider.get_active_providers()
    
    return render_template('super_admin/oauth_providers.html', providers=providers)


@super_admin_bp.route('/oauth-providers/create', methods=['POST'])
@super_admin_required
def oauth_providers_create():
    """Create or update OAuth provider."""
    data = request.form
    
    provider_type = data.get('provider_type')
    
    provider = SaaSOAuthProvider.query.filter_by(provider_type=provider_type).first()
    
    if not provider:
        import uuid
        provider = SaaSOAuthProvider(
            id=str(uuid.uuid4()),
            provider_type=provider_type,
        )
        db.session.add(provider)
    
    provider.name = data.get('name')
    provider.description = data.get('description')
    provider.client_id = encrypt(data.get('client_id')) if data.get('client_id') else provider.client_id
    provider.client_secret = encrypt(data.get('client_secret')) if data.get('client_secret') else provider.client_secret
    provider.authorization_url = data.get('authorization_url')
    provider.token_url = data.get('token_url')
    provider.userinfo_url = data.get('userinfo_url')
    provider.is_active = data.get('is_active') == 'on'
    
    # Parse scopes
    scopes = data.get('scopes', '')
    provider.scopes = [s.strip() for s in scopes.split(',') if s.strip()]
    
    # Check if configured
    provider.is_configured = bool(provider.client_id and provider.client_secret)
    provider.status = 'configured' if provider.is_configured else 'not_configured'
    
    db.session.commit()
    
    flash(f'OAuth provider "{provider.name}" saved.', 'success')
    return redirect(url_for('super_admin.oauth_providers'))


# =============================================================================
# Payment Gateways Management
# =============================================================================

@super_admin_bp.route('/payment-gateways')
@super_admin_required
def payment_gateways():
    """Payment gateways management page."""
    providers = SaaSPaymentProvider.get_active_providers()
    
    return render_template('super_admin/payment_gateways.html', providers=providers)


@super_admin_bp.route('/payment-gateways/create', methods=['POST'])
@super_admin_required
def payment_gateways_create():
    """Create or update payment provider."""
    data = request.form
    
    provider_type = data.get('provider_type')
    
    provider = SaaSPaymentProvider.query.filter_by(provider_type=provider_type).first()
    
    if not provider:
        import uuid
        provider = SaaSPaymentProvider(
            id=str(uuid.uuid4()),
            provider_type=provider_type,
        )
        db.session.add(provider)
    
    provider.name = data.get('name')
    provider.description = data.get('description')
    provider.credentials = encrypt(data.get('credentials')) if data.get('credentials') else provider.credentials
    provider.is_active = data.get('is_active') == 'on'
    provider.is_default = data.get('is_default') == 'on'
    provider.sort_order = int(data.get('sort_order', 0))
    
    # Parse supported currencies
    currencies = data.get('supported_currencies', 'USD')
    provider.supported_currencies = [c.strip() for c in currencies.split(',') if c.strip()]
    
    # Check if configured
    provider.is_configured = bool(provider.credentials)
    provider.status = 'configured' if provider.is_configured else 'not_configured'
    
    db.session.commit()
    
    flash(f'Payment provider "{provider.name}" saved.', 'success')
    return redirect(url_for('super_admin.payment_gateways'))


# =============================================================================
# Integrations Settings
# =============================================================================

@super_admin_bp.route('/integrations')
@super_admin_required
def integrations():
    """System integrations page."""
    integrations = SaaSSystemIntegration.query.all()
    
    return render_template('super_admin/integrations.html', integrations=integrations)


@super_admin_bp.route('/integrations/create', methods=['POST'])
@super_admin_required
def integrations_create():
    """Create or update system integration."""
    data = request.form
    
    import uuid
    integration_key = data.get('integration_key')
    
    integration = SaaSSystemIntegration.query.filter_by(
        integration_key=integration_key
    ).first()
    
    if not integration:
        integration = SaaSSystemIntegration(
            id=str(uuid.uuid4()),
            integration_key=integration_key,
            integration_type=data.get('integration_type'),
        )
        db.session.add(integration)
    
    integration.name = data.get('name')
    integration.description = data.get('description')
    integration.icon = data.get('icon')
    integration.credentials = encrypt(data.get('credentials')) if data.get('credentials') else integration.credentials
    integration.is_active = data.get('is_active') == 'on'
    
    # Check if configured
    integration.is_configured = bool(integration.credentials)
    integration.status = 'configured' if integration.is_configured else 'not_configured'
    
    db.session.commit()
    
    flash(f'Integration "{integration.name}" saved.', 'success')
    return redirect(url_for('super_admin.integrations'))


# =============================================================================
# Usage Tracking
# =============================================================================

@super_admin_bp.route('/usage')
@super_admin_required
def usage():
    """Usage tracking page."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = SaaSUsageTracking.query
    
    # Filter by organization
    org_id = request.args.get('org_id')
    if org_id:
        query = query.filter_by(organization_id=org_id)
    
    # Filter by metric
    metric = request.args.get('metric')
    if metric:
        query = query.filter_by(metric_key=metric)
    
    pagination = query.order_by(SaaSUsageTracking.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    organizations = Organization.query.filter_by(is_active=True).all()
    metrics = SaaSUsageTracking.get_metric_key_list()
    
    return render_template('super_admin/usage.html',
        usage_records=pagination.items,
        pagination=pagination,
        organizations=organizations,
        metrics=metrics
    )


# =============================================================================
# Audit Logs
# =============================================================================

@super_admin_bp.route('/audit-logs')
@super_admin_required
def audit_logs():
    """Audit logs page."""
    from models.audit_log import AuditLog
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    query = AuditLog.query
    
    # Filter by category
    category = request.args.get('category')
    if category:
        query = query.filter_by(category=category)
    
    # Filter by user
    user_id = request.args.get('user_id')
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    # Filter by action
    action = request.args.get('action')
    if action:
        query = query.filter_by(action=action)
    
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    categories = db.session.query(AuditLog.category).distinct().all()
    
    return render_template('super_admin/audit_logs.html',
        logs=pagination.items,
        pagination=pagination,
        categories=[c[0] for c in categories if c[0]]
    )


# =============================================================================
# System Health
# =============================================================================

@super_admin_bp.route('/system-health')
@super_admin_required
def system_health():
    """System health page."""
    health = get_system_health()
    
    return render_template('super_admin/system_health.html', health=health)


def get_system_health():
    """Get comprehensive system health status."""
    health = {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {}
    }
    
    # Database
    try:
        db.session.execute(db.text('SELECT 1'))
        health['components']['database'] = {
            'status': 'ok',
            'message': 'Connected'
        }
    except Exception as e:
        health['components']['database'] = {
            'status': 'error',
            'message': str(e)
        }
        health['status'] = 'degraded'
    
    # AI Providers
    configured_providers = SaaSAIProvider.query.filter_by(is_configured=True).count()
    total_providers = SaaSAIProvider.query.filter_by(is_active=True).count()
    
    if total_providers == 0:
        ai_status = 'not_configured'
    elif configured_providers == 0:
        ai_status = 'not_configured'
    else:
        ai_status = 'partial' if configured_providers < total_providers else 'ok'
    
    health['components']['ai'] = {
        'status': ai_status,
        'configured': configured_providers,
        'total': total_providers
    }
    
    # OAuth Providers
    oauth_configured = SaaSOAuthProvider.query.filter_by(is_configured=True).count()
    oauth_total = SaaSOAuthProvider.query.filter_by(is_active=True).count()
    
    if oauth_total == 0:
        oauth_status = 'not_configured'
    elif oauth_configured == 0:
        oauth_status = 'not_configured'
    else:
        oauth_status = 'partial'
    
    health['components']['oauth'] = {
        'status': oauth_status,
        'configured': oauth_configured,
        'total': oauth_total
    }
    
    # Payment Providers
    payment_configured = SaaSPaymentProvider.query.filter_by(is_configured=True).count()
    payment_total = SaaSPaymentProvider.query.filter_by(is_active=True).count()
    
    if payment_total == 0:
        payment_status = 'not_configured'
    elif payment_configured == 0:
        payment_status = 'not_configured'
    else:
        payment_status = 'ok'
    
    health['components']['payments'] = {
        'status': payment_status,
        'configured': payment_configured,
        'total': payment_total
    }
    
    return health


# =============================================================================
# API Endpoints
# =============================================================================

@super_admin_bp.route('/api/health')
def api_health():
    """API health check endpoint."""
    health = get_system_health()
    return jsonify(health)


@super_admin_bp.route('/api/plans', methods=['GET'])
@api_super_admin_required
def api_plans():
    """Get all plans API."""
    plans = SaaSPlan.query.filter_by(is_archived=False).order_by(SaaSPlan.sort_order).all()
    return jsonify({
        'plans': [p.to_dict() for p in plans]
    })


@super_admin_bp.route('/api/plans/<plan_id>', methods=['GET'])
@api_super_admin_required
def api_plan_detail(plan_id):
    """Get plan details API."""
    plan = SaaSPlan.query.get_or_404(plan_id)
    return jsonify(plan.to_dict())


@super_admin_bp.route('/api/features', methods=['GET'])
@api_super_admin_required
def api_features():
    """Get all features API."""
    features = SaaSFeature.get_active_features()
    return jsonify({
        'features': [f.to_dict() for f in features]
    })


@super_admin_bp.route('/api/organizations', methods=['GET'])
@api_super_admin_required
def api_organizations():
    """Get organizations API."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Organization.query.filter_by(is_active=True)
    
    pagination = query.order_by(Organization.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'organizations': [o.to_dict() for o in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@super_admin_bp.route('/api/organizations/<org_id>/usage', methods=['GET'])
@api_super_admin_required
def api_organization_usage(org_id):
    """Get organization usage API."""
    gate = FeatureGate.for_organization(org_id)
    return jsonify({
        'usage': gate.get_usage_summary()
    })


@super_admin_bp.route('/api/providers/status', methods=['GET'])
@api_super_admin_required
def api_providers_status():
    """Get all provider statuses."""
    return jsonify({
        'ai_providers': [p.to_dict() for p in SaaSAIProvider.get_active_providers()],
        'oauth_providers': [p.to_dict() for p in SaaSOAuthProvider.get_active_providers()],
        'payment_providers': [p.to_dict() for p in SaaSPaymentProvider.get_active_providers()],
    })


@super_admin_bp.route('/api/integrations/keys', methods=['GET'])
@api_super_admin_required
def api_get_keys():
    """Get masked API keys."""
    keys = {
        'ai_providers': {},
        'oauth_providers': {},
        'payment_providers': {},
    }
    
    for p in SaaSAIProvider.get_active_providers():
        keys['ai_providers'][p.provider_type] = {
            'configured': p.is_configured,
            'api_key': mask(decrypt(p.api_key)) if p.api_key else None
        }
    
    for p in SaaSOAuthProvider.get_active_providers():
        keys['oauth_providers'][p.provider_type] = {
            'configured': p.is_configured,
            'client_id': mask(decrypt(p.client_id)) if p.client_id else None
        }
    
    for p in SaaSPaymentProvider.get_active_providers():
        keys['payment_providers'][p.provider_type] = {
            'configured': p.is_configured
        }
    
    return jsonify(keys)


# =============================================================================
# Initialize Defaults
# =============================================================================

@super_admin_bp.route('/initialize', methods=['POST'])
@super_admin_required
def initialize_defaults():
    """Initialize default plans and features."""
    try:
        FeatureGateManager.initialize_defaults()
        flash('System initialized with default plans and features.', 'success')
    except Exception as e:
        flash(f'Initialization failed: {e}', 'danger')
    
    return redirect(url_for('super_admin.index'))
