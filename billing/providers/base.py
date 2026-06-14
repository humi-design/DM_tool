"""Abstract payment provider interface for billing system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, List, Any
from enum import Enum


class PaymentProviderType(Enum):
    """Payment provider types."""
    STRIPE = "stripe"
    RAZORPAY = "razorpay"


@dataclass
class CustomerData:
    """Customer data for payment provider."""
    email: str
    name: str
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PaymentMethodData:
    """Payment method data."""
    type: str  # card, bank_transfer, etc.
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    wallet_name: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PaymentIntentData:
    """Payment intent data."""
    id: str
    amount: Decimal
    currency: str
    status: str
    client_secret: Optional[str] = None
    payment_method_id: Optional[str] = None
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class SubscriptionData:
    """Subscription data."""
    id: str
    customer_id: str
    price_id: str
    status: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool = False
    trial_end: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class InvoiceData:
    """Invoice data from provider."""
    id: str
    number: str
    amount: Decimal
    currency: str
    status: str
    customer_id: str
    subscription_id: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    pdf_url: Optional[str] = None
    hosted_url: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PriceData:
    """Price/product data."""
    id: str
    name: str
    amount: Decimal
    currency: str
    interval: str  # month, year
    interval_count: int = 1
    trial_days: int = 0
    metadata: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class RefundData:
    """Refund data."""
    id: str
    amount: Decimal
    currency: str
    status: str
    reason: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class PaymentProviderError(Exception):
    """Base exception for payment provider errors."""
    
    def __init__(self, message: str, code: str = None, provider: str = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.provider = provider


class PaymentProvider(ABC):
    """Abstract payment provider interface."""
    
    provider_type: PaymentProviderType = None
    
    def __init__(self, api_key: str = None, secret_key: str = None, 
                 webhook_secret: str = None, **config):
        """Initialize payment provider."""
        self.api_key = api_key
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        self.config = config
    
    # ============ Customer Management ============
    
    @abstractmethod
    def create_customer(self, customer_data: CustomerData) -> str:
        """Create a customer in the payment provider. Returns customer ID."""
        pass
    
    @abstractmethod
    def get_customer(self, customer_id: str) -> CustomerData:
        """Get customer data from provider."""
        pass
    
    @abstractmethod
    def update_customer(self, customer_id: str, customer_data: CustomerData) -> None:
        """Update customer data."""
        pass
    
    @abstractmethod
    def delete_customer(self, customer_id: str) -> None:
        """Delete a customer."""
        pass
    
    # ============ Payment Methods ============
    
    @abstractmethod
    def attach_payment_method(self, payment_method_id: str, customer_id: str) -> None:
        """Attach payment method to customer."""
        pass
    
    @abstractmethod
    def detach_payment_method(self, payment_method_id: str) -> None:
        """Detach payment method from customer."""
        pass
    
    @abstractmethod
    def list_payment_methods(self, customer_id: str) -> List[PaymentMethodData]:
        """List customer's payment methods."""
        pass
    
    @abstractmethod
    def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> None:
        """Set default payment method for customer."""
        pass
    
    # ============ Payment Intents ============
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Get payment intent data."""
        pass
    
    @abstractmethod
    def confirm_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Confirm a payment intent."""
        pass
    
    @abstractmethod
    def cancel_payment_intent(self, payment_intent_id: str) -> PaymentIntentData:
        """Cancel a payment intent."""
        pass
    
    # ============ Subscriptions ============
    
    @abstractmethod
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
        metadata: Dict[str, Any] = None
    ) -> SubscriptionData:
        """Create a subscription."""
        pass
    
    @abstractmethod
    def get_subscription(self, subscription_id: str) -> SubscriptionData:
        """Get subscription data."""
        pass
    
    @abstractmethod
    def update_subscription(
        self,
        subscription_id: str,
        price_id: str = None,
        quantity: int = None,
        metadata: Dict[str, Any] = None
    ) -> SubscriptionData:
        """Update subscription."""
        pass
    
    @abstractmethod
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> SubscriptionData:
        """Cancel subscription."""
        pass
    
    @abstractmethod
    def pause_subscription(self, subscription_id: str) -> SubscriptionData:
        """Pause subscription."""
        pass
    
    @abstractmethod
    def resume_subscription(self, subscription_id: str) -> SubscriptionData:
        """Resume subscription."""
        pass
    
    # ============ Products & Prices ============
    
    @abstractmethod
    def create_product(
        self,
        name: str,
        description: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a product. Returns product ID."""
        pass
    
    @abstractmethod
    def create_price(
        self,
        product_id: str,
        amount: Decimal,
        currency: str,
        interval: str,  # month, year
        interval_count: int = 1,
        trial_days: int = 0,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create a price. Returns price ID."""
        pass
    
    @abstractmethod
    def get_price(self, price_id: str) -> PriceData:
        """Get price data."""
        pass
    
    # ============ Invoices ============
    
    @abstractmethod
    def get_invoice(self, invoice_id: str) -> InvoiceData:
        """Get invoice data."""
        pass
    
    @abstractmethod
    def get_upcoming_invoice(
        self,
        customer_id: str,
        subscription_id: str = None
    ) -> InvoiceData:
        """Get upcoming invoice for customer."""
        pass
    
    @abstractmethod
    def finalize_invoice(self, invoice_id: str) -> InvoiceData:
        """Finalize a draft invoice."""
        pass
    
    @abstractmethod
    def void_invoice(self, invoice_id: str) -> InvoiceData:
        """Void an invoice."""
        pass
    
    # ============ Refunds ============
    
    @abstractmethod
    def create_refund(
        self,
        payment_intent_id: str,
        amount: Decimal = None,
        reason: str = None
    ) -> RefundData:
        """Create a refund."""
        pass
    
    # ============ Webhooks ============
    
    @abstractmethod
    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """Construct and verify webhook event."""
        pass
    
    @abstractmethod
    def get_webhook_event_type(self, event: Dict[str, Any]) -> str:
        """Get event type from webhook event."""
        pass
    
    # ============ Checkout Sessions ============
    
    @abstractmethod
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
        pass
    
    # ============ Utility Methods ============
    
    def format_amount(self, amount: Decimal, currency: str) -> int:
        """Format amount for provider API (usually in smallest currency unit)."""
        # Most providers use smallest unit (cents for USD)
        return int(amount * 100)
    
    def parse_amount(self, amount: int, currency: str) -> Decimal:
        """Parse amount from provider API."""
        return Decimal(amount) / 100
    
    def get_currency_multiplier(self, currency: str) -> int:
        """Get currency multiplier for smallest unit."""
        zero_decimal_currencies = {"JPY", "KRW", "VND", "IDR"}
        if currency.upper() in zero_decimal_currencies:
            return 1
        return 100


class PaymentProviderFactory:
    """Factory for creating payment providers."""
    
    _providers: Dict[PaymentProviderType, type] = {}
    
    @classmethod
    def register(cls, provider_type: PaymentProviderType, provider_class: type):
        """Register a payment provider class."""
        cls._providers[provider_type] = provider_class
    
    @classmethod
    def create(
        cls,
        provider_type: PaymentProviderType,
        **config
    ) -> PaymentProvider:
        """Create a payment provider instance."""
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown payment provider: {provider_type}")
        
        return cls._providers[provider_type](**config)
    
    @classmethod
    def get_available_providers(cls) -> List[PaymentProviderType]:
        """Get list of available provider types."""
        return list(cls._providers.keys())


# Decorator for registering providers
def register_payment_provider(provider_type: PaymentProviderType):
    """Decorator for registering payment providers."""
    def decorator(cls):
        PaymentProviderFactory.register(provider_type, cls)
        return cls
    return decorator