"""Razorpay payment provider implementation."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, List, Any

import razorpay

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


@register_payment_provider(PaymentProviderType.RAZORPAY)
class RazorpayProvider(PaymentProvider):
    """Razorpay payment provider implementation."""
    
    provider_type = PaymentProviderType.RAZORPAY
    
    def __init__(self, api_key: str = None, secret_key: str = None, webhook_secret: str = None, **config):
        super().__init__(api_key, secret_key, webhook_secret, **config)
        if api_key and secret_key:
            self.client = razorpay.Client(auth=(api_key, secret_key))
        else:
            self.client = None
        self.webhook_secret = webhook_secret
    
    def _handle_razorpay_error(self, error: Exception) -> PaymentProviderError:
        """Convert Razorpay error to PaymentProviderError."""
        error_code = None
        error_msg = str(error)
        
        if isinstance(error, razorpay.errors.BadRequestError):
            error_code = "BAD_REQUEST"
        elif isinstance(error, razorpay.errors.AuthenticationError):
            error_code = "AUTH_ERROR"
        elif isinstance(error, razorpay.errors.ServerError):
            error_code = "SERVER_ERROR"
        elif isinstance(error, razorpay.errors.RazorpayError):
            error_code = getattr(error, "code", "RAZORPAY_ERROR")
        
        return PaymentProviderError(
            message=error_msg,
            code=error_code,
            provider="razorpay"
        )
    
    # ============ Customer Management ============
    
    def create_customer(self, customer_data: CustomerData) -> str:
        """Create a customer in Razorpay."""
        try:
            data = {
                "name": customer_data.name,
                "email": customer_data.email,
            }
            if customer_data.phone:
                data["phone"] = customer_data.phone
            if customer_data.metadata:
                data["notes"] = customer_data.metadata
            
            customer = self.client.customer.create(data=data)
            return customer["id"]
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def get_customer(self, customer_id: str) -> CustomerData:
        """Get customer data from Razorpay."""
        try:
            customer = self.client.customer.fetch(customer_id)
            return CustomerData(
                email=customer.get("email"),
                name=customer.get("name"),
                phone=customer.get("phone"),
                metadata=customer.get("notes")
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def update_customer(self, customer_id: str, customer_data: CustomerData) -> None:
        """Update customer data."""
        try:
            data = {
                "name": customer_data.name,
                "email": customer_data.email,
            }
            if customer_data.phone:
                data["phone"] = customer_data.phone
            if customer_data.metadata:
                data["notes"] = customer_data.metadata
            
            self.client.customer.edit(customer_id, data)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def delete_customer(self, customer_id: str) -> None:
        """Delete a customer (not supported in Razorpay, raise error)."""
        raise PaymentProviderError(
            message="Customer deletion not supported by Razorpay",
            code="UNSUPPORTED",
            provider="razorpay"
        )
    
    # ============ Payment Methods ============
    
    def attach_payment_method(self, payment_method_id: str, customer_id: str) -> None:
        """Attach payment method to customer."""
        try:
            self.client.customer.fetch(customer_id)
            # Razorpay uses tokens for saving cards
            pass
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def detach_payment_method(self, payment_method_id: str) -> None:
        """Detach payment method from customer."""
        try:
            self.client.customer.delete_token(
                payment_method_id.split("_")[0],  # customer_id
                payment_method_id.split("_")[1]   # token_id
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def list_payment_methods(self, customer_id: str) -> List[PaymentMethodData]:
        """List customer's payment methods."""
        try:
            tokens = self.client.customer.fetch(customer_id).get("tokens", {}).get("entities", [])
            return [
                PaymentMethodData(
                    type="card",
                    card_brand=token.get("card", {}).get("network"),
                    card_last4=token.get("card", {}).get("last4"),
                    card_exp_month=token.get("card", {}).get("expiry_month"),
                    card_exp_year=token.get("card", {}).get("expiry_year"),
                    raw_data=token
                )
                for token in tokens if token.get("entity") == "token"
            ]
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> None:
        """Set default payment method for customer."""
        # Razorpay doesn't support default payment method directly
        pass
    
    # ============ Payment Intents (Orders in Razorpay) ============
    
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method_id: str = None,
        metadata: Dict[str, Any] = None,
        description: str = None
    ) -> PaymentIntentData:
        """Create a payment order (Razorpay's equivalent of payment intent)."""
        try:
            data = {
                "amount": self.format_amount(amount, currency),
                "currency": currency.upper(),
                "customer_id": customer_id,
                "notes": metadata or {},
            }
            if description:
                data["description"] = description
            
            order = self.client.order.create(data=data)
            return PaymentIntentData(
                id=order["id"],
                amount=Decimal(order["amount"]) / 100,
                currency=order["currency"],
                status=order["status"],
                customer_id=customer_id,
                metadata=metadata,
                raw_data=order
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def get_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Get payment order data."""
        try:
            order = self.client.order.fetch(payment_intent_id)
            return PaymentIntentData(
                id=order["id"],
                amount=Decimal(order["amount"]) / 100,
                currency=order["currency"],
                status=order["status"],
                customer_id=order.get("customer_id"),
                metadata=order.get("notes"),
                raw_data=order
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def confirm_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """For Razorpay, capture payment."""
        try:
            payments = self.client.order.fetch(payment_intent_id).get("payments", {})
            if payments and payments.get("entities"):
                payment = payments["entities"][0]
                captured = self.client.payment.capture(
                    payment["id"],
                    {"amount": payment["amount"]}
                )
                return PaymentIntentData(
                    id=payment_intent_id,
                    amount=Decimal(captured["amount"]) / 100,
                    currency=captured["currency"],
                    status="succeeded" if captured["status"] == "captured" else captured["status"],
                    customer_id=captured.get("customer_id"),
                    raw_data=captured
                )
            return self.get_payment_intent(payment_intent_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def cancel_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Cancel a payment order."""
        try:
            order = self.client.order.fetch(payment_intent_id)
            if order["status"] == "created":
                self.client.order.cancel(payment_intent_id)
            return self.get_payment_intent(payment_intent_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
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
            data = {
                "plan_id": price_id,
                "customer_id": customer_id,
                "total_count": 120,  # 10 years max
                "notes": metadata or {},
            }
            if trial_days > 0:
                data["trial_period"] = trial_days
            
            subscription = self.client.subscription.create(data=data)
            return SubscriptionData(
                id=subscription["id"],
                customer_id=customer_id,
                price_id=price_id,
                status=subscription["status"],
                current_period_start=datetime.fromtimestamp(subscription["current_start"]).isoformat(),
                current_period_end=datetime.fromtimestamp(subscription["current_end"]).isoformat(),
                trial_end=datetime.fromtimestamp(subscription["trial_end"]).isoformat() if subscription.get("trial_end") else None,
                metadata=metadata,
                raw_data=subscription
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def get_subscription(self, subscription_id: str) -> SubscriptionData:
        """Get subscription data."""
        try:
            sub = self.client.subscription.fetch(subscription_id)
            return SubscriptionData(
                id=sub["id"],
                customer_id=sub["customer_id"],
                price_id=sub["plan_id"],
                status=sub["status"],
                current_period_start=datetime.fromtimestamp(sub["current_start"]).isoformat(),
                current_period_end=datetime.fromtimestamp(sub["current_end"]).isoformat(),
                cancel_at_period_end=sub.get("cancel_at_period_end", False),
                trial_end=datetime.fromtimestamp(sub["trial_end"]).isoformat() if sub.get("trial_end") else None,
                metadata=sub.get("notes"),
                raw_data=sub
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def update_subscription(
        self,
        subscription_id: str,
        price_id: str = None,
        quantity: int = None,
        metadata: Dict[str, Any] = None
    ) -> SubscriptionData:
        """Update subscription."""
        try:
            data = {}
            if price_id:
                data["plan_id"] = price_id
            if metadata:
                data["notes"] = metadata
            
            if data:
                self.client.subscription.edit(subscription_id, data)
            
            return self.get_subscription(subscription_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> SubscriptionData:
        """Cancel subscription."""
        try:
            if at_period_end:
                self.client.subscription.pause(subscription_id)
            else:
                self.client.subscription.cancel(subscription_id)
            return self.get_subscription(subscription_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def pause_subscription(self, subscription_id: str) -> SubscriptionData:
        """Pause subscription."""
        try:
            self.client.subscription.pause(subscription_id)
            return self.get_subscription(subscription_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def resume_subscription(self, subscription_id: str) -> SubscriptionData:
        """Resume subscription."""
        try:
            self.client.subscription.resume(subscription_id)
            return self.get_subscription(subscription_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    # ============ Products & Prices (Plans in Razorpay) ============
    
    def create_product(
        self,
        name: str,
        description: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a product (not directly supported, use plan as product)."""
        return name  # Return name as identifier
    
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
        """Create a plan (Razorpay's price equivalent)."""
        try:
            data = {
                "period": "monthly" if interval == "month" else "yearly",
                "interval": interval_count,
                "item": {
                    "name": product_id,
                    "amount": self.format_amount(amount, currency),
                    "currency": currency.upper(),
                },
                "notes": metadata or {},
            }
            
            plan = self.client.plan.create(data=data)
            return plan["id"]
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def get_price(self, price_id: str) -> PriceData:
        """Get plan data."""
        try:
            plan = self.client.plan.fetch(price_id)
            item = plan.get("item", {})
            return PriceData(
                id=plan["id"],
                name=item.get("name"),
                amount=Decimal(item.get("amount", 0)) / 100,
                currency=item.get("currency", "INR"),
                interval=plan.get("period"),
                interval_count=plan.get("interval", 1),
                metadata=plan.get("notes"),
                raw_data=plan
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    # ============ Invoices ============
    
    def get_invoice(self, invoice_id: str) -> InvoiceData:
        """Get invoice data."""
        try:
            invoice = self.client.invoice.fetch(invoice_id)
            return self._invoice_to_data(invoice)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def get_upcoming_invoice(
        self,
        customer_id: str,
        subscription_id: str = None
    ) -> InvoiceData:
        """Get upcoming invoice for customer."""
        try:
            if subscription_id:
                sub = self.client.subscription.fetch(subscription_id)
                # Create a subscription charge invoice
                data = {
                    "type": "subscription",
                    "subscription_id": subscription_id,
                }
                upcoming = self.client.invoice.create(data=data)
                return self._invoice_to_data(upcoming)
            raise PaymentProviderError(
                message="Subscription ID required for upcoming invoice",
                code="INVALID_REQUEST",
                provider="razorpay"
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def finalize_invoice(self, invoice_id: str) -> InvoiceData:
        """Finalize a draft invoice."""
        try:
            self.client.invoice.notify_by(invoice_id)
            return self.get_invoice(invoice_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def void_invoice(self, invoice_id: str) -> InvoiceData:
        """Void an invoice."""
        try:
            self.client.invoice.cancel(invoice_id)
            return self.get_invoice(invoice_id)
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    def _invoice_to_data(self, invoice) -> InvoiceData:
        """Convert Razorpay invoice to InvoiceData."""
        return InvoiceData(
            id=invoice["id"],
            number=invoice.get("number"),
            amount=Decimal(invoice.get("amount_due", 0)) / 100,
            currency=invoice.get("currency", "INR"),
            status=invoice.get("status"),
            customer_id=invoice.get("customer_id"),
            subscription_id=invoice.get("subscription_id"),
            period_start=datetime.fromtimestamp(invoice["period_start"]).isoformat() if invoice.get("period_start") else None,
            period_end=datetime.fromtimestamp(invoice["period_end"]).isoformat() if invoice.get("period_end") else None,
            due_date=datetime.fromtimestamp(invoice["due_date"]).isoformat() if invoice.get("due_date") else None,
            pdf_url=invoice.get("invoice_url"),
            hosted_url=invoice.get("short_url"),
            line_items=invoice.get("line_items", []),
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
            data = {}
            if amount:
                data["amount"] = self.format_amount(amount, "inr")
            if reason:
                data["notes"] = {"reason": reason}
            
            refund = self.client.payment.refund(payment_intent_id, data)
            return RefundData(
                id=refund["id"],
                amount=Decimal(refund["amount"]) / 100,
                currency=refund["currency"],
                status=refund["status"],
                reason=reason,
                raw_data=refund
            )
        except Exception as e:
            raise self._handle_razorpay_error(e)
    
    # ============ Webhooks ============
    
    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Construct and verify webhook event."""
        import hmac
        import hashlib
        
        try:
            generated_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(generated_signature, signature):
                raise PaymentProviderError(
                    message="Invalid webhook signature",
                    code="INVALID_SIGNATURE",
                    provider="razorpay"
                )
            
            import json
            return json.loads(payload)
        except Exception as e:
            if isinstance(e, PaymentProviderError):
                raise
            raise PaymentProviderError(
                message=str(e),
                code="WEBHOOK_ERROR",
                provider="razorpay"
            )
    
    def get_webhook_event_type(self, event: Dict[str, Any]) -> str:
        """Get event type from webhook event."""
        return event.get("event")
    
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
        """Create a checkout session (Razorpay Checkout)."""
        try:
            customer = self.client.customer.fetch(customer_id)
            sub = self.client.subscription.fetch(price_id)
            
            return {
                "rzp_order_id": sub.get("id"),
                "customer_id": customer_id,
                "customer_email": customer.get("email"),
                "amount": sub.get("amount_due", 0) / 100,
                "currency": sub.get("currency", "INR"),
            }
        except Exception as e:
            raise self._handle_razorpay_error(e)