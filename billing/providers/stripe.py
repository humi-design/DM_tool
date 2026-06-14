"""Stripe payment provider implementation."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any

import stripe

from billing.providers.base import (
    PaymentProvider,
    PaymentProviderError,
    PaymentProviderType,
    register_payment_provider,
    CustomerData,
    PaymentMethodData,
    PaymentIntentData,
    SubscriptionData,
    InvoiceData,
    PriceData,
    RefundData,
)


@register_payment_provider(PaymentProviderType.STRIPE)
class StripeProvider(PaymentProvider):
    """Stripe payment provider implementation."""
    
    provider_type = PaymentProviderType.STRIPE
    
    def __init__(self, api_key: str = None, webhook_secret: str = None, **config):
        super().__init__(api_key, webhook_secret=webhook_secret, **config)
        if api_key:
            stripe.api_key = api_key
        self.webhook_secret = webhook_secret
    
    def _handle_stripe_error(self, error: stripe.StripeError) -> PaymentProviderError:
        """Convert Stripe error to PaymentProviderError."""
        return PaymentProviderError(
            message=str(error.user_message or error),
            code=getattr(error, 'code', None),
            provider="stripe"
        )
    
    # ============ Customer Management ============
    
    def create_customer(self, customer_data: CustomerData) -> str:
        """Create a customer in Stripe."""
        try:
            customer = stripe.Customer.create(
                email=customer_data.email,
                name=customer_data.name,
                phone=customer_data.phone,
                address=customer_data.address,
                metadata=customer_data.metadata or {}
            )
            return customer.id
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def get_customer(self, customer_id: str) -> CustomerData:
        """Get customer data from Stripe."""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return CustomerData(
                email=customer.email,
                name=customer.name,
                phone=customer.phone,
                address=customer.address,
                metadata=customer.metadata
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def update_customer(self, customer_id: str, customer_data: CustomerData) -> None:
        """Update customer data."""
        try:
            stripe.Customer.modify(
                customer_id,
                email=customer_data.email,
                name=customer_data.name,
                phone=customer_data.phone,
                address=customer_data.address,
                metadata=customer_data.metadata
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def delete_customer(self, customer_id: str) -> None:
        """Delete a customer."""
        try:
            stripe.Customer.delete(customer_id)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    # ============ Payment Methods ============
    
    def attach_payment_method(self, payment_method_id: str, customer_id: str) -> None:
        """Attach payment method to customer."""
        try:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def detach_payment_method(self, payment_method_id: str) -> None:
        """Detach payment method from customer."""
        try:
            stripe.PaymentMethod.detach(payment_method_id)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def list_payment_methods(self, customer_id: str) -> List[PaymentMethodData]:
        """List customer's payment methods."""
        try:
            methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            return [
                PaymentMethodData(
                    type="card",
                    card_brand=pm.card.brand if pm.card else None,
                    card_last4=pm.card.last4 if pm.card else None,
                    card_exp_month=pm.card.exp_month if pm.card else None,
                    card_exp_year=pm.card.exp_year if pm.card else None,
                    raw_data=pm
                )
                for pm in methods.data
            ]
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> None:
        """Set default payment method for customer."""
        try:
            stripe.Customer.modify(
                customer_id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    # ============ Payment Intents ============
    
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method_id: str = None,
        metadata: Dict[str, Any] = None,
        description: str = None
    ) -> PaymentIntentData:
        """Create a payment intent."""
        try:
            params = {
                "amount": self.format_amount(amount, currency),
                "currency": currency.lower(),
                "customer": customer_id,
                "metadata": metadata or {},
            }
            if payment_method_id:
                params["payment_method"] = payment_method_id
                params["confirm"] = True
            if description:
                params["description"] = description
            
            intent = stripe.PaymentIntent.create(**params)
            return PaymentIntentData(
                id=intent.id,
                amount=Decimal(intent.amount) / 100,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                customer_id=intent.customer,
                metadata=intent.metadata,
                raw_data=intent
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def get_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Get payment intent data."""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return PaymentIntentData(
                id=intent.id,
                amount=Decimal(intent.amount) / 100,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                customer_id=intent.customer,
                metadata=intent.metadata,
                raw_data=intent
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def confirm_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Confirm a payment intent."""
        try:
            intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return PaymentIntentData(
                id=intent.id,
                amount=Decimal(intent.amount) / 100,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                customer_id=intent.customer,
                metadata=intent.metadata,
                raw_data=intent
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def cancel_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Cancel a payment intent."""
        try:
            intent = stripe.PaymentIntent.cancel(payment_intent_id)
            return PaymentIntentData(
                id=intent.id,
                amount=Decimal(intent.amount) / 100,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                customer_id=intent.customer,
                metadata=intent.metadata,
                raw_data=intent
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    # ============ Subscriptions ============
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
        metadata: Dict[str, Any] = None
    ) -> SubscriptionData:
        """Create a subscription."""
        try:
            params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {},
            }
            if trial_days > 0:
                params["trial_period_days"] = trial_days
            
            subscription = stripe.Subscription.create(**params)
            return self._subscription_to_data(subscription)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def get_subscription(self, subscription_id: str) -> SubscriptionData:
        """Get subscription data."""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return self._subscription_to_data(subscription)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def update_subscription(
        self,
        subscription_id: str,
        price_id: str = None,
        quantity: int = None,
        metadata: Dict[str, Any] = None
    ) -> SubscriptionData:
        """Update subscription."""
        try:
            params = {}
            if price_id:
                params["items"] = [{"price": price_id}]
            if metadata:
                params["metadata"] = metadata
            
            subscription = stripe.Subscription.modify(subscription_id, **params)
            return self._subscription_to_data(subscription)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> SubscriptionData:
        """Cancel subscription."""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            return self._subscription_to_data(subscription)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def pause_subscription(self, subscription_id: str) -> SubscriptionData:
        """Pause subscription."""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                pause_collection={"behavior": "void"}
            )
            return self._subscription_to_data(subscription)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def resume_subscription(self, subscription_id: str) -> SubscriptionData:
        """Resume subscription."""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                pause_collection=""
            )
            return self._subscription_to_data(subscription)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def _subscription_to_data(self, subscription) -> SubscriptionData:
        """Convert Stripe subscription to SubscriptionData."""
        return SubscriptionData(
            id=subscription.id,
            customer_id=subscription.customer,
            price_id=subscription.items.data[0].price.id if subscription.items.data else None,
            status=subscription.status,
            current_period_start=datetime.fromtimestamp(subscription.current_period_start).isoformat(),
            current_period_end=datetime.fromtimestamp(subscription.current_period_end).isoformat(),
            cancel_at_period_end=subscription.cancel_at_period_end,
            trial_end=datetime.fromtimestamp(subscription.trial_end).isoformat() if subscription.trial_end else None,
            metadata=subscription.metadata,
            raw_data=subscription
        )
    
    # ============ Products & Prices ============
    
    def create_product(
        self,
        name: str,
        description: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a product."""
        try:
            product = stripe.Product.create(
                name=name,
                description=description,
                metadata=metadata or {}
            )
            return product.id
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def create_price(
        self,
        product_id: str,
        amount: Decimal,
        currency: str,
        interval: str,
        interval_count: int = 1,
        trial_days: int = 0,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a price."""
        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=int(amount * 100),
                currency=currency.lower(),
                recurring={
                    "interval": interval,
                    "interval_count": interval_count,
                },
                metadata=metadata or {}
            )
            return price.id
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def get_price(self, price_id: str) -> PriceData:
        """Get price data."""
        try:
            price = stripe.Price.retrieve(price_id, expand=["product"])
            return PriceData(
                id=price.id,
                name=price.product.name,
                amount=Decimal(price.unit_amount) / 100,
                currency=price.currency,
                interval=price.recurring.interval,
                interval_count=price.recurring.interval_count,
                metadata=price.metadata,
                raw_data=price
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    # ============ Invoices ============
    
    def get_invoice(self, invoice_id: str) -> InvoiceData:
        """Get invoice data."""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return self._invoice_to_data(invoice)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def get_upcoming_invoice(
        self,
        customer_id: str,
        subscription_id: str = None
    ) -> InvoiceData:
        """Get upcoming invoice for customer."""
        try:
            params = {"customer": customer_id}
            if subscription_id:
                params["subscription"] = subscription_id
            
            invoice = stripe.Invoice.upcoming(**params)
            return self._invoice_to_data(invoice)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def finalize_invoice(self, invoice_id: str) -> InvoiceData:
        """Finalize a draft invoice."""
        try:
            invoice = stripe.Invoice.finalize_invoice(invoice_id)
            return self._invoice_to_data(invoice)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def void_invoice(self, invoice_id: str) -> InvoiceData:
        """Void an invoice."""
        try:
            invoice = stripe.Invoice.void_invoice(invoice_id)
            return self._invoice_to_data(invoice)
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def _invoice_to_data(self, invoice) -> InvoiceData:
        """Convert Stripe invoice to InvoiceData."""
        return InvoiceData(
            id=invoice.id,
            number=invoice.number,
            amount=Decimal(invoice.amount_due) / 100,
            currency=invoice.currency,
            status=invoice.status,
            customer_id=invoice.customer,
            subscription_id=invoice.subscription,
            period_start=datetime.fromtimestamp(invoice.period_start).isoformat() if invoice.period_start else None,
            period_end=datetime.fromtimestamp(invoice.period_end).isoformat() if invoice.period_end else None,
            due_date=datetime.fromtimestamp(invoice.due_date).isoformat() if invoice.due_date else None,
            paid_at=datetime.fromtimestamp(invoice.status_transitions.paid_at).isoformat() if invoice.status_transitions.paid_at else None,
            pdf_url=invoice.invoice_pdf,
            hosted_url=invoice.hosted_invoice_url,
            line_items=[
                {
                    "description": item.description,
                    "amount": Decimal(item.amount) / 100,
                    "quantity": item.quantity
                }
                for item in invoice.lines.data
            ] if invoice.lines else None,
            raw_data=invoice
        )
    
    # ============ Refunds ============
    
    def create_refund(
        self,
        payment_intent_id: str,
        amount: Decimal = None,
        reason: str = None
    ) -> RefundData:
        """Create a refund."""
        try:
            params = {"payment_intent": payment_intent_id}
            if amount:
                params["amount"] = self.format_amount(amount, "usd")
            if reason:
                params["reason"] = reason
            
            refund = stripe.Refund.create(**params)
            return RefundData(
                id=refund.id,
                amount=Decimal(refund.amount) / 100,
                currency=refund.currency,
                status=refund.status,
                reason=refund.reason,
                raw_data=refund
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    # ============ Webhooks ============
    
    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Construct and verify webhook event."""
        try:
            return stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)
    
    def get_webhook_event_type(self, event: Dict[str, Any]) -> str:
        """Get event type from webhook event."""
        return event.get("type")
    
    # ============ Checkout Sessions ============
    
    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        trial_days: int = 0,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a checkout session."""
        try:
            params = {
                "customer": customer_id,
                "line_items": [{"price": price_id, "quantity": 1}],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata or {},
            }
            if trial_days > 0:
                params["subscription_data"] = {"trial_period_days": trial_days}
            
            session = stripe.checkout.Session.create(**params)
            return {
                "session_id": session.id,
                "url": session.url
            }
        except stripe.StripeError as e:
            raise self._handle_stripe_error(e)