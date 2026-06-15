"""Dynamic SaaS Platform Tables

Revision ID: 20260615_dynamic_saas
Revises: 7e1c0ff90743
Create Date: 2026-06-15

This migration adds all tables needed for the fully dynamic,
multi-tenant SaaS platform architecture.

Tables:
- plans (dynamic plan management)
- features (dynamic feature definitions)
- plan_features (plan-feature associations)
- plan_limits (plan-based limits)
- organization_overrides (customer-specific limit overrides)
- pricing_cards (customizable pricing page cards)
- system_integrations (all configurable integrations)
- payment_providers (dynamic payment gateway config)
- oauth_providers (dynamic OAuth provider config)
- webhooks (generic webhook management)
- webhook_deliveries (webhook delivery tracking)
- usage_tracking (detailed usage metrics)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '20260615_dynamic_saas'
down_revision: Union[str, Sequence[str], None] = '7e1c0ff90743'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dynamic SaaS platform tables."""
    
    # =======================================================================
    # PLANS TABLE - Dynamic plan management
    # =======================================================================
    op.create_table(
        'saas_plans',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('price_annual', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('billing_cycle', sa.String(20), nullable=False, default='monthly'),
        sa.Column('trial_days', sa.Integer(), nullable=False, default=0),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, default=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_plan_slug', 'saas_plans', ['slug'], unique=True)
    op.create_index('idx_saas_plan_active_order', 'saas_plans', ['is_active', 'is_archived', 'sort_order'])
    
    # =======================================================================
    # FEATURES TABLE - Dynamic feature definitions
    # =======================================================================
    op.create_table(
        'saas_features',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('feature_name', sa.String(100), nullable=False),
        sa.Column('feature_key', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('is_module', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_addon', sa.Boolean(), nullable=False, default=False),
        sa.Column('addon_price_monthly', sa.Numeric(10, 2), nullable=True),
        sa.Column('addon_price_annual', sa.Numeric(10, 2), nullable=True),
        sa.Column('tracks_usage', sa.Boolean(), nullable=False, default=False),
        sa.Column('usage_unit', sa.String(50), nullable=True),
        sa.Column('usage_included', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_feature_key', 'saas_features', ['feature_key'], unique=True)
    op.create_index('idx_saas_feature_category_active', 'saas_features', ['category', 'is_active'])
    
    # =======================================================================
    # PLAN_FEATURES TABLE - Plan-feature associations
    # =======================================================================
    op.create_table(
        'saas_plan_features',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('plan_id', sa.String(36), sa.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature_id', sa.String(36), sa.ForeignKey('saas_features.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('plan_id', 'feature_id', name='uq_plan_feature'),
    )
    op.create_index('idx_saas_plan_feature_plan', 'saas_plan_features', ['plan_id'])
    op.create_index('idx_saas_plan_feature_feature', 'saas_plan_features', ['feature_id'])
    
    # =======================================================================
    # PLAN_LIMITS TABLE - Dynamic limits per plan
    # =======================================================================
    op.create_table(
        'saas_plan_limits',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('plan_id', sa.String(36), sa.ForeignKey('saas_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('limit_key', sa.String(100), nullable=False),
        sa.Column('limit_value', sa.Integer(), nullable=False),
        sa.Column('period', sa.String(20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_plan_limits_plan', 'saas_plan_limits', ['plan_id'])
    op.create_index('idx_saas_plan_limits_key', 'saas_plan_limits', ['limit_key'])
    op.create_index('idx_saas_plan_limits_plan_key', 'saas_plan_limits', ['plan_id', 'limit_key'], unique=True)
    
    # =======================================================================
    # ORGANIZATION_OVERRIDES TABLE - Customer-specific overrides
    # =======================================================================
    op.create_table(
        'saas_organization_overrides',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature_key', sa.String(100), nullable=True),
        sa.Column('limit_key', sa.String(100), nullable=True),
        sa.Column('custom_limit', sa.Integer(), nullable=True),
        sa.Column('custom_value', sa.String(255), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_org_overrides_org', 'saas_organization_overrides', ['organization_id'])
    op.create_index('idx_saas_org_overrides_expires', 'saas_organization_overrides', ['expires_at'])
    op.create_index('idx_saas_org_overrides_org_feature', 'saas_organization_overrides', ['organization_id', 'feature_key'])
    op.create_index('idx_saas_org_overrides_org_limit', 'saas_organization_overrides', ['organization_id', 'limit_key'])
    
    # =======================================================================
    # PRICING_CARDS TABLE - Customizable pricing page
    # =======================================================================
    op.create_table(
        'saas_pricing_cards',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('plan_id', sa.String(36), sa.ForeignKey('saas_plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('subtitle', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('badge', sa.String(50), nullable=True),
        sa.Column('button_text', sa.String(50), nullable=False, default='Get Started'),
        sa.Column('button_url', sa.String(255), nullable=True),
        sa.Column('theme', sa.String(50), nullable=False, default='default'),
        sa.Column('features', sa.JSON(), nullable=False, default=list),
        sa.Column('display_order', sa.Integer(), nullable=False, default=0),
        sa.Column('is_visible', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_highlighted', sa.Boolean(), nullable=False, default=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_pricing_cards_order', 'saas_pricing_cards', ['display_order', 'is_visible'])
    op.create_index('idx_saas_pricing_cards_plan', 'saas_pricing_cards', ['plan_id'])
    
    # =======================================================================
    # SYSTEM_INTEGRATIONS TABLE - Centralized credentials
    # =======================================================================
    op.create_table(
        'saas_system_integrations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('integration_type', sa.String(50), nullable=False),
        sa.Column('integration_key', sa.String(100), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('credentials', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False, default=dict),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_configured', sa.Boolean(), nullable=False, default=False),
        sa.Column('status', sa.String(50), nullable=False, default='not_configured'),
        sa.Column('last_tested_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_integrations_type', 'saas_system_integrations', ['integration_type'])
    op.create_index('idx_saas_integrations_key', 'saas_system_integrations', ['integration_key'], unique=True)
    op.create_index('idx_saas_integrations_active', 'saas_system_integrations', ['is_active', 'status'])
    
    # =======================================================================
    # PAYMENT_PROVIDERS TABLE - Dynamic payment gateway config
    # =======================================================================
    op.create_table(
        'saas_payment_providers',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('credentials', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False, default=dict),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_configured', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('status', sa.String(50), nullable=False, default='not_configured'),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('webhook_url', sa.String(255), nullable=True),
        sa.Column('supported_currencies', sa.JSON(), nullable=False, default=list),
        sa.Column('supported_payment_methods', sa.JSON(), nullable=False, default=list),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_payment_providers_type', 'saas_payment_providers', ['provider_type'])
    op.create_index('idx_saas_payment_providers_active', 'saas_payment_providers', ['is_active', 'is_default', 'sort_order'])
    
    # =======================================================================
    # OAUTH_PROVIDERS TABLE - Dynamic OAuth provider config
    # =======================================================================
    op.create_table(
        'saas_oauth_providers',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('client_id', sa.Text(), nullable=True),
        sa.Column('client_secret', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False, default=dict),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_configured', sa.Boolean(), nullable=False, default=False),
        sa.Column('status', sa.String(50), nullable=False, default='not_configured'),
        sa.Column('scopes', sa.JSON(), nullable=False, default=list),
        sa.Column('authorization_url', sa.String(255), nullable=True),
        sa.Column('token_url', sa.String(255), nullable=True),
        sa.Column('userinfo_url', sa.String(255), nullable=True),
        sa.Column('redirect_urls', sa.JSON(), nullable=False, default=list),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_oauth_providers_type', 'saas_oauth_providers', ['provider_type'])
    op.create_index('idx_saas_oauth_providers_active', 'saas_oauth_providers', ['is_active', 'status'])
    
    # =======================================================================
    # AI_PROVIDERS TABLE - Dynamic AI provider config
    # =======================================================================
    op.create_table(
        'saas_ai_providers',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(255), nullable=True),
        sa.Column('default_model', sa.String(100), nullable=True),
        sa.Column('available_models', sa.JSON(), nullable=False, default=list),
        sa.Column('config', sa.JSON(), nullable=False, default=dict),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_configured', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('status', sa.String(50), nullable=False, default='not_configured'),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('timeout', sa.Float(), nullable=False, default=60.0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('rate_limit', sa.Integer(), nullable=True),
        sa.Column('supports_vision', sa.Boolean(), nullable=False, default=False),
        sa.Column('supports_function_calling', sa.Boolean(), nullable=False, default=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_ai_providers_type', 'saas_ai_providers', ['provider_type'])
    op.create_index('idx_saas_ai_providers_active_priority', 'saas_ai_providers', ['is_active', 'priority'])
    
    # =======================================================================
    # WEBHOOKS TABLE - Generic webhook management
    # =======================================================================
    op.create_table(
        'saas_webhooks',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('secret', sa.Text(), nullable=True),
        sa.Column('events', sa.JSON(), nullable=False, default=list),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('headers', sa.JSON(), nullable=False, default=dict),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_webhooks_provider', 'saas_webhooks', ['provider'])
    op.create_index('idx_saas_webhooks_active', 'saas_webhooks', ['is_active'])
    
    # =======================================================================
    # WEBHOOK_DELIVERIES TABLE - Webhook delivery tracking
    # =======================================================================
    op.create_table(
        'saas_webhook_deliveries',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('webhook_id', sa.String(36), sa.ForeignKey('saas_webhooks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_id', sa.String(100), nullable=True),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=False, default=5),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('signature_valid', sa.Boolean(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, default=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_webhook_deliveries_webhook', 'saas_webhook_deliveries', ['webhook_id'])
    op.create_index('idx_saas_webhook_deliveries_status', 'saas_webhook_deliveries', ['status'])
    op.create_index('idx_saas_webhook_deliveries_event', 'saas_webhook_deliveries', ['event_type', 'created_at'])
    
    # =======================================================================
    # USAGE_TRACKING TABLE - Detailed usage metrics
    # =======================================================================
    op.create_table(
        'saas_usage_tracking',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_key', sa.String(100), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False, default='monthly'),
        sa.Column('used', sa.Integer(), nullable=False, default=0),
        sa.Column('included', sa.Integer(), nullable=True),
        sa.Column('overage', sa.Integer(), nullable=False, default=0),
        sa.Column('unit_cost', sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column('overage_cost', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('last_reset_at', sa.DateTime(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_usage_org_metric', 'saas_usage_tracking', ['organization_id', 'metric_key', 'period_start'])
    op.create_index('idx_saas_usage_period', 'saas_usage_tracking', ['period_start', 'period_end'])
    
    # =======================================================================
    # SUBSCRIPTION_INVOICES TABLE - Enhanced invoice tracking
    # =======================================================================
    op.create_table(
        'saas_invoices',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscription_id', sa.String(36), sa.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('payment_provider', sa.String(50), nullable=True),
        sa.Column('payment_transaction_id', sa.String(255), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('billing_period_start', sa.DateTime(), nullable=True),
        sa.Column('billing_period_end', sa.DateTime(), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('line_items', sa.JSON(), nullable=False, default=list),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_invoices_org', 'saas_invoices', ['organization_id'])
    op.create_index('idx_saas_invoices_number', 'saas_invoices', ['invoice_number'], unique=True)
    op.create_index('idx_saas_invoices_status', 'saas_invoices', ['status'])
    
    # =======================================================================
    # TRANSACTIONS TABLE - Payment transaction tracking
    # =======================================================================
    op.create_table(
        'saas_transactions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invoice_id', sa.String(36), sa.ForeignKey('saas_invoices.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('transaction_id', sa.String(255), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('gateway_response', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_saas_transactions_org', 'saas_transactions', ['organization_id'])
    op.create_index('idx_saas_transactions_provider', 'saas_transactions', ['provider', 'transaction_id'])
    op.create_index('idx_saas_transactions_status', 'saas_transactions', ['status'])
    
    # =======================================================================
    # Add SUPER_ADMIN role column to users table
    # =======================================================================
    op.add_column('users', sa.Column('role', sa.String(50), nullable=False, server_default='user'))
    op.create_index('idx_users_role', 'users', ['role'])


def downgrade() -> None:
    """Remove dynamic SaaS platform tables."""
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('saas_transactions')
    op.drop_table('saas_invoices')
    op.drop_table('saas_usage_tracking')
    op.drop_table('saas_webhook_deliveries')
    op.drop_table('saas_webhooks')
    op.drop_table('saas_ai_providers')
    op.drop_table('saas_oauth_providers')
    op.drop_table('saas_payment_providers')
    op.drop_table('saas_system_integrations')
    op.drop_table('saas_pricing_cards')
    op.drop_table('saas_organization_overrides')
    op.drop_table('saas_plan_limits')
    op.drop_table('saas_plan_features')
    op.drop_table('saas_features')
    op.drop_table('saas_plans')
    
    # Remove SUPER_ADMIN role column
    op.drop_index('idx_users_role', 'users')
    op.drop_column('users', 'role')
