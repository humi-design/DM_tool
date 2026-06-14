"""Billing service layer for managing subscriptions, payments, and usage."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Any, Tuple
import logging

from app import db
from models.subscription import Subscription
from models.plan import Plan, PlanFeature, OrganizationFeature
from models.invoice import Invoice
from models.payment import Payment
from models.usage import UsageRecord, OrganizationUsage
from models.organization import Organization

from billing.providers import (
    PaymentProviderFactory,
    PaymentProviderType,
    PaymentProvider,
    PaymentProviderError,
    CustomerData,
)

logger = logging.getLogger(__name__)


class BillingService:
    """Service for managing billing operations."""
    
    def __init__(self, provider_type: str = "stripe"):
        """Initialize billing service."""
        self.provider_type = provider_type
        self._provider = None
    
    @property
    def provider(self) -> PaymentProvider:
        """Get payment provider."""
        if self._provider is None:
            from flask import current_app
            config = current_app.config
            
            if self.provider_type == "stripe":
                api_key = config.get("STRIPE_API_KEY")
                webhook_secret = config.get("STRIPE_WEBHOOK_SECRET")
                self._provider = PaymentProviderFactory.create(
                    PaymentProviderType.STRIPE,
                    api_key=api_key,
                    webhook_secret=webhook_secret
                )
            elif self.provider_type == "razorpay":
                api_key = config.get("RAZORPAY_API_KEY")
                secret_key = config.get("RAZORPAY_SECRET_KEY")
                webhook_secret = config.get("RAZORPAY_WEBHOOK_SECRET")
                self._provider = PaymentProviderFactory.create(
                    PaymentProviderType.RAZORPAY,
                    api_key=api_key,
                    secret_key=secret_key,
                    webhook_secret=webhook_secret
                )
        
        return self._provider
    
    def set_provider(self, provider: PaymentProvider):
        """Set payment provider (for testing)."""
        self._provider = provider
    
    # ============ Customer Management ============
    
    def create_customer(self, organization: Organization) -> str:
        """Create customer in payment provider."""
        customer_data = CustomerData(
            email=organization.owner.email if organization.owner else "unknown@example.com",
            name=organization.name,
            metadata={"organization_id": organization.id}
        )
        
        try:
            customer_id = self.provider.create_customer(customer_data)
            organization.metadata_json["payment_customer_id"] = customer_id
            db.session.commit()
            return customer_id
        except PaymentProviderError as e:
            logger.error(f"Failed to create customer: {e}")
            raise
    
    def get_customer_id(self, organization: Organization) -> Optional[str]:
        """Get or create customer ID for organization."""
        customer_id = organization.metadata_json.get("payment_customer_id")
        if not customer_id:
            customer_id = self.create_customer(organization)
        return customer_id
    
    # ============ Subscription Management ============
    
    def create_subscription(
        self,
        organization: Organization,
        plan: Plan,
        billing_cycle: str = "monthly",
        trial_days: int = None
    ) -> Subscription:
        """Create a new subscription."""
        customer_id = self.get_customer_id(organization)
        
        # Get price ID from plan (stored in metadata)
        price_id = plan.metadata_json.get(f"price_id_{billing_cycle}")
        if not price_id:
            raise ValueError(f"Price not configured for plan {plan.slug} and cycle {billing_cycle}")
        
        trial_days = trial_days if trial_days is not None else plan.trial_days
        
        try:
            # Create subscription in provider
            sub_data = self.provider.create_subscription(
                customer_id=customer_id,
                price_id=price_id,
                trial_days=trial_days,
                metadata={
                    "organization_id": organization.id,
                    "plan_slug": plan.slug
                }
            )
            
            # Calculate billing period
            period_start = datetime.fromisoformat(sub_data.current_period_start)
            period_end = datetime.fromisoformat(sub_data.current_period_end)
            
            if billing_cycle == "annual":
                period_end = period_start + timedelta(days=365)
            
            # Calculate price
            unit_price = plan.get_monthly_price(billing_cycle)
            if billing_cycle == "annual":
                unit_price = float(plan.price_annual) / 12
            
            # Create subscription record
            subscription = Subscription(
                organization_id=organization.id,
                plan_id=plan.id,
                plan_name=plan.name,
                status=self._map_subscription_status(sub_data.status),
                billing_cycle=billing_cycle,
                billing_period_start=period_start,
                billing_period_end=period_end,
                trial_start=datetime.utcnow() if trial_days > 0 else None,
                trial_end=datetime.fromisoformat(sub_data.trial_end) if sub_data.trial_end else None,
                unit_price=Decimal(str(unit_price)),
                total_amount=Decimal(str(unit_price)),
                currency=plan.currency,
                external_subscription_id=sub_data.id,
                external_customer_id=customer_id
            )
            
            db.session.add(subscription)
            
            # Update organization plan
            organization.plan = plan.slug
            organization.plan_expires_at = period_end
            
            db.session.commit()
            
            # Initialize features based on plan
            self._initialize_plan_features(organization, plan)
            
            return subscription
            
        except PaymentProviderError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise
    
    def _map_subscription_status(self, provider_status: str) -> str:
        """Map provider status to internal status."""
        mapping = {
            "active": Subscription.STATUS_ACTIVE,
            "trialing": Subscription.STATUS_TRIALING,
            "past_due": Subscription.STATUS_PAST_DUE,
            "canceled": Subscription.STATUS_CANCELED,
            "unpaid": Subscription.STATUS_PAST_DUE,
            "incomplete": Subscription.STATUS_PAST_DUE,
        }
        return mapping.get(provider_status.lower(), Subscription.STATUS_ACTIVE)
    
    def cancel_subscription(
        self,
        subscription: Subscription,
        at_period_end: bool = True
    ) -> Subscription:
        """Cancel a subscription."""
        try:
            if subscription.external_subscription_id:
                self.provider.cancel_subscription(
                    subscription.external_subscription_id,
                    at_period_end=at_period_end
                )
            
            subscription.cancel(at_period_end=at_period_end)
            return subscription
            
        except PaymentProviderError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise
    
    def change_plan(
        self,
        subscription: Subscription,
        new_plan: Plan,
        billing_cycle: str = None
    ) -> Subscription:
        """Change subscription plan."""
        billing_cycle = billing_cycle or subscription.billing_cycle
        price_id = new_plan.metadata_json.get(f"price_id_{billing_cycle}")
        
        if not price_id:
            raise ValueError(f"Price not configured for plan {new_plan.slug}")
        
        try:
            if subscription.external_subscription_id:
                self.provider.update_subscription(
                    subscription_id=subscription.external_subscription_id,
                    price_id=price_id
                )
            
            # Update subscription record
            subscription.plan_id = new_plan.id
            subscription.plan_name = new_plan.name
            subscription.unit_price = Decimal(str(new_plan.get_monthly_price(billing_cycle)))
            subscription.total_amount = subscription.unit_price
            
            db.session.commit()
            
            # Update organization
            subscription.organization.plan = new_plan.slug
            
            # Update features
            self._initialize_plan_features(subscription.organization, new_plan)
            
            return subscription
            
        except PaymentProviderError as e:
            logger.error(f"Failed to change plan: {e}")
            raise
    
    def _initialize_plan_features(self, organization: Organization, plan: Plan) -> None:
        """Initialize organization features based on plan."""
        # Disable all current features
        OrganizationFeature.query.filter_by(organization_id=organization.id).update(
            {"is_enabled": False}
        )
        
        # Enable features from plan
        for feature_slug, enabled in plan.features.items():
            if enabled:
                feature = PlanFeature.get_by_slug(feature_slug)
                if feature:
                    org_feature = OrganizationFeature.query.filter_by(
                        organization_id=organization.id,
                        feature_id=feature.id
                    ).first()
                    
                    if not org_feature:
                        org_feature = OrganizationFeature(
                            organization_id=organization.id,
                            feature_id=feature.id,
                            is_enabled=True
                        )
                        db.session.add(org_feature)
                    else:
                        org_feature.is_enabled = True
        
        db.session.commit()
    
    # ============ Payment Processing ============
    
    def create_checkout_session(
        self,
        organization: Organization,
        plan: Plan,
        billing_cycle: str = "monthly",
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """Create checkout session for subscription."""
        customer_id = self.get_customer_id(organization)
        price_id = plan.metadata_json.get(f"price_id_{billing_cycle}")
        
        if not price_id:
            raise ValueError(f"Price not configured for plan {plan.slug}")
        
        try:
            return self.provider.create_checkout_session(
                customer_id=customer_id,
                price_id=price_id,
                success_url=success_url,
                cancel_url=cancel_url,
                trial_days=plan.trial_days,
                metadata={"organization_id": organization.id}
            )
        except PaymentProviderError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise
    
    def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Handle webhook from payment provider."""
        try:
            event = self.provider.construct_webhook_event(payload, signature)
            event_type = self.provider.get_webhook_event_type(event)
            
            self._process_webhook_event(event_type, event)
            
            return {"received": True}
        except PaymentProviderError as e:
            logger.error(f"Webhook error: {e}")
            raise
    
    def _process_webhook_event(self, event_type: str, event: Dict[str, Any]) -> None:
        """Process webhook event."""
        data = event.get("data", {}).get("object", {})
        
        if "subscription" in event_type:
            self._handle_subscription_event(event_type, data)
        elif "invoice" in event_type:
            self._handle_invoice_event(event_type, data)
        elif "payment_intent" in event_type or "payment" in event_type:
            self._handle_payment_event(event_type, data)
        elif "customer" in event_type:
            self._handle_customer_event(event_type, data)
    
    def _handle_subscription_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle subscription-related webhook events."""
        external_id = data.get("id")
        subscription = Subscription.query.filter_by(
            external_subscription_id=external_id
        ).first()
        
        if not subscription:
            return
        
        if "updated" in event_type:
            subscription.status = self._map_subscription_status(data.get("status"))
            db.session.commit()
        elif "deleted" in event_type:
            subscription.status = Subscription.STATUS_CANCELED
            subscription.canceled_at = datetime.utcnow()
            db.session.commit()
    
    def _handle_invoice_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle invoice-related webhook events."""
        # Implementation for invoice webhooks
        pass
    
    def _handle_payment_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle payment-related webhook events."""
        # Implementation for payment webhooks
        pass
    
    def _handle_customer_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle customer-related webhook events."""
        # Implementation for customer webhooks
        pass


class PlanService:
    """Service for managing pricing plans."""
    
    @staticmethod
    def get_plans(include_inactive: bool = False) -> List[Plan]:
        """Get all active plans."""
        query = Plan.query
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(Plan.sort_order).all()
    
    @staticmethod
    def get_plan_by_slug(slug: str) -> Optional[Plan]:
        """Get plan by slug."""
        return Plan.get_by_slug(slug)
    
    @staticmethod
    def create_plan(
        name: str,
        slug: str,
        price_monthly: float,
        price_annual: float,
        features: Dict[str, Any],
        **kwargs
    ) -> Plan:
        """Create a new plan."""
        plan = Plan(
            name=name,
            slug=slug,
            price_monthly=Decimal(str(price_monthly)),
            price_annual=Decimal(str(price_annual)),
            features=features,
            **kwargs
        )
        db.session.add(plan)
        db.session.commit()
        return plan
    
    @staticmethod
    def get_plan_features(plan: Plan) -> Dict[str, Any]:
        """Get plan features with details."""
        features = {}
        for slug, enabled in plan.features.items():
            feature = PlanFeature.get_by_slug(slug)
            if feature:
                features[slug] = {
                    "name": feature.name,
                    "description": feature.description,
                    "enabled": enabled,
                    "icon": feature.icon
                }
        return features


class UsageService:
    """Service for tracking and managing usage."""
    
    @staticmethod
    def record_usage(
        organization_id: str,
        usage_type: str,
        count: int = 1,
        subscription_id: str = None
    ) -> UsageRecord:
        """Record usage for an organization."""
        # Update organization usage
        org_usage = OrganizationUsage.get_or_create_current(organization_id)
        org_usage.increment(usage_type, count)
        
        # Create or update usage record
        record = UsageRecord.get_or_create_current(
            organization_id=organization_id,
            usage_type=usage_type,
            subscription_id=subscription_id
        )
        record.add_usage(count, {"source": "api"})
        
        return record
    
    @staticmethod
    def get_usage_summary(
        organization_id: str,
        plan: Plan = None
    ) -> Dict[str, Any]:
        """Get usage summary for organization."""
        org_usage = OrganizationUsage.get_or_create_current(organization_id)
        
        summary = {
            "api_requests": {
                "used": org_usage.api_requests,
                "limit": plan.max_api_requests_per_month if plan else None,
                "percentage": 0
            },
            "ai_requests": {
                "used": org_usage.ai_requests,
                "limit": plan.max_ai_requests_per_month if plan else None,
                "percentage": 0
            },
            "storage_mb": {
                "used": org_usage.storage_mb,
                "limit": plan.max_storage_mb if plan else None,
                "percentage": 0
            },
            "messages_sent": {
                "used": org_usage.messages_sent,
                "limit": None,
                "percentage": 0
            },
            "leads_captured": {
                "used": org_usage.leads_captured,
                "limit": None,
                "percentage": 0
            },
        }
        
        # Calculate percentages
        for key, data in summary.items():
            if data["limit"]:
                data["percentage"] = min(100, (data["used"] / data["limit"]) * 100)
        
        return summary
    
    @staticmethod
    def check_usage_limit(
        organization_id: str,
        usage_type: str,
        plan: Plan = None
    ) -> Tuple[bool, str]:
        """Check if usage is within limits."""
        if not plan:
            return True, "No limits"
        
        org_usage = OrganizationUsage.get_or_create_current(organization_id)
        
        limits_map = {
            "api_requests": plan.max_api_requests_per_month,
            "ai_requests": plan.max_ai_requests_per_month,
            "storage_mb": plan.max_storage_mb,
        }
        
        limit = limits_map.get(usage_type)
        if limit is None:
            return True, "Unlimited"
        
        current_usage = getattr(org_usage, usage_type, 0)
        if current_usage >= limit:
            return False, f"Usage limit exceeded ({current_usage}/{limit})"
        
        return True, "OK"
    
    @staticmethod
    def get_usage_history(
        organization_id: str,
        days: int = 90
    ) -> List[UsageRecord]:
        """Get usage history for organization."""
        start_date = datetime.utcnow() - timedelta(days=days)
        return UsageRecord.query.filter(
            UsageRecord.organization_id == organization_id,
            UsageRecord.period_start >= start_date
        ).order_by(UsageRecord.period_start.desc()).all()


class FeatureService:
    """Service for managing feature flags and add-ons."""
    
    @staticmethod
    def get_organization_features(organization_id: str) -> List[OrganizationFeature]:
        """Get all features for an organization."""
        return OrganizationFeature.query.filter_by(
            organization_id=organization_id
        ).all()
    
    @staticmethod
    def is_feature_enabled(
        organization_id: str,
        feature_slug: str
    ) -> bool:
        """Check if a feature is enabled for organization."""
        feature = PlanFeature.get_by_slug(feature_slug)
        if not feature:
            return False
        
        org_feature = OrganizationFeature.query.filter_by(
            organization_id=organization_id,
            feature_id=feature.id
        ).first()
        
        if not org_feature:
            # Check if feature is in plan
            org = Organization.query.get(organization_id)
            plan = Plan.get_by_slug(org.plan)
            if plan and plan.has_feature(feature_slug):
                return True
            return False
        
        if org_feature.is_trial and org_feature.is_trial_expired():
            return False
        
        return org_feature.is_enabled
    
    @staticmethod
    def enable_feature(
        organization_id: str,
        feature_slug: str,
        as_trial: bool = False,
        trial_days: int = 14
    ) -> OrganizationFeature:
        """Enable a feature for organization."""
        feature = PlanFeature.get_by_slug(feature_slug)
        if not feature:
            raise ValueError(f"Feature not found: {feature_slug}")
        
        org_feature = OrganizationFeature.query.filter_by(
            organization_id=organization_id,
            feature_id=feature.id
        ).first()
        
        if not org_feature:
            org_feature = OrganizationFeature(
                organization_id=organization_id,
                feature_id=feature.id
            )
            db.session.add(org_feature)
        
        org_feature.is_enabled = True
        org_feature.is_trial = as_trial
        org_feature.trial_ends_at = (
            datetime.utcnow() + timedelta(days=trial_days) if as_trial else None
        )
        
        db.session.commit()
        return org_feature
    
    @staticmethod
    def disable_feature(
        organization_id: str,
        feature_slug: str
    ) -> None:
        """Disable a feature for organization."""
        feature = PlanFeature.get_by_slug(feature_slug)
        if not feature:
            return
        
        org_feature = OrganizationFeature.query.filter_by(
            organization_id=organization_id,
            feature_id=feature.id
        ).first()
        
        if org_feature:
            org_feature.is_enabled = False
            db.session.commit()
    
    @staticmethod
    def start_feature_trial(
        organization_id: str,
        feature_slug: str,
        trial_days: int = 14
    ) -> OrganizationFeature:
        """Start a trial for a feature."""
        return FeatureService.enable_feature(
            organization_id=organization_id,
            feature_slug=feature_slug,
            as_trial=True,
            trial_days=trial_days
        )