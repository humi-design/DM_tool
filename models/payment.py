"""Payment model for billing payments."""

from datetime import datetime
from decimal import Decimal

from app import db
from models.base import BaseModel


class Payment(BaseModel):
    """Payment model for tracking payments."""
    
    __tablename__ = "payments"
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    invoice_id = db.Column(
        db.String(36),
        db.ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    subscription_id = db.Column(
        db.String(36),
        db.ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Payment identification
    payment_intent_id = db.Column(db.String(255), nullable=True, unique=True, index=True)
    external_payment_id = db.Column(db.String(255), nullable=True, index=True)
    
    # Status and method
    status = db.Column(db.String(50), default="pending", nullable=False, index=True)
    payment_method = db.Column(db.String(50), nullable=True, index=True)
    payment_method_type = db.Column(db.String(50), nullable=True)  # card, bank_transfer, etc.
    
    # Amount
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    
    # Fees
    processing_fee = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Gateway info
    payment_gateway = db.Column(db.String(50), nullable=True, index=True)  # stripe, razorpay, etc.
    gateway_response = db.Column(db.JSON, default=dict, nullable=False)
    
    # Payment details
    card_brand = db.Column(db.String(50), nullable=True)
    card_last4 = db.Column(db.String(4), nullable=True)
    card_exp_month = db.Column(db.Integer, nullable=True)
    card_exp_year = db.Column(db.Integer, nullable=True)
    
    # Billing details
    billing_name = db.Column(db.String(255), nullable=True)
    billing_email = db.Column(db.String(255), nullable=True)
    billing_address = db.Column(db.JSON, default=dict, nullable=False)
    
    # Timing
    attempted_at = db.Column(db.DateTime, nullable=True, index=True)
    processed_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Error handling
    failure_code = db.Column(db.String(100), nullable=True)
    failure_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Refund info
    refunded_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    refund_reason = db.Column(db.Text, nullable=True)
    refunded_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    
    # Relationships
    organization = db.relationship("Organization", back_populates="payments")
    invoice = db.relationship("Invoice", back_populates="payments")
    subscription = db.relationship("Subscription", back_populates="payments")
    
    __table_args__ = (
        db.Index("idx_payment_org_status", "organization_id", "status"),
        db.Index("idx_payment_status_date", "status", "processed_at"),
        db.Index("idx_payment_gateway_id", "payment_gateway", "external_payment_id"),
    )
    
    # Status constants
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_PARTIALLY_REFUNDED = "partially_refunded"
    STATUS_CANCELED = "canceled"
    STATUS_VOID = "void"
    
    # Payment method types
    METHOD_CARD = "card"
    METHOD_BANK_TRANSFER = "bank_transfer"
    METHOD_ACH = "ach"
    METHOD_UPI = "upi"
    METHOD_WALLET = "wallet"
    
    # Gateway constants
    GATEWAY_STRIPE = "stripe"
    GATEWAY_RAZORPAY = "razorpay"
    
    def to_dict(self, include_gateway_response: bool = False):
        """Convert payment to dictionary."""
        data = super().to_dict()
        if not include_gateway_response:
            data.pop("gateway_response", None)
        return data
    
    @property
    def is_succeeded(self) -> bool:
        """Check if payment succeeded."""
        return self.status == self.STATUS_SUCCEEDED
    
    @property
    def is_failed(self) -> bool:
        """Check if payment failed."""
        return self.status == self.STATUS_FAILED
    
    @property
    def is_refunded(self) -> bool:
        """Check if payment was refunded."""
        return self.status in (self.STATUS_REFUNDED, self.STATUS_PARTIALLY_REFUNDED)
    
    @property
    def is_refundable(self) -> bool:
        """Check if payment can be refunded."""
        if self.status != self.STATUS_SUCCEEDED:
            return False
        if self.refunded_amount and Decimal(str(self.refunded_amount)) >= self.amount:
            return False
        # Check if within refund window (90 days)
        if self.processed_at:
            days_since = (datetime.utcnow() - self.processed_at).days
            return days_since <= 90
        return False
    
    @property
    def refund_available(self) -> Decimal:
        """Get amount available for refund."""
        return Decimal(str(self.amount)) - Decimal(str(self.refunded_amount or 0))
    
    @property
    def masked_card(self) -> str:
        """Get masked card number."""
        if self.card_last4:
            return f"**** **** **** {self.card_last4}"
        return None
    
    def mark_succeeded(self, gateway_response: dict = None) -> None:
        """Mark payment as succeeded."""
        self.status = self.STATUS_SUCCEEDED
        self.processed_at = datetime.utcnow()
        if gateway_response:
            self.gateway_response = gateway_response
        db.session.commit()
    
    def mark_failed(self, failure_code: str, failure_message: str) -> None:
        """Mark payment as failed."""
        self.status = self.STATUS_FAILED
        self.failure_code = failure_code
        self.failure_message = failure_message
        db.session.commit()
    
    def mark_processing(self) -> None:
        """Mark payment as processing."""
        self.status = self.STATUS_PROCESSING
        self.attempted_at = datetime.utcnow()
        db.session.commit()
    
    def refund(self, amount: Decimal = None, reason: str = None) -> None:
        """Process refund."""
        refund_amount = amount or self.refund_available
        self.refunded_amount = Decimal(str(self.refunded_amount or 0)) + refund_amount
        self.refund_reason = reason
        self.refunded_at = datetime.utcnow()
        
        if self.refunded_amount >= self.amount:
            self.status = self.STATUS_REFUNDED
        else:
            self.status = self.STATUS_PARTIALLY_REFUNDED
        
        db.session.commit()
    
    @classmethod
    def get_successful_payments(cls, organization_id: str, limit: int = 10):
        """Get successful payments for organization."""
        return cls.query.filter(
            cls.organization_id == organization_id,
            cls.status == cls.STATUS_SUCCEEDED
        ).order_by(cls.processed_at.desc()).limit(limit).all()
    
    @classmethod
    def get_failed_payments(cls, organization_id: str):
        """Get failed payments for organization."""
        return cls.query.filter(
            cls.organization_id == organization_id,
            cls.status == cls.STATUS_FAILED
        ).order_by(cls.attempted_at.desc()).all()
    
    @classmethod
    def get_total_revenue(cls, organization_id: str = None) -> Decimal:
        """Calculate total revenue."""
        query = cls.query.filter(cls.status == cls.STATUS_SUCCEEDED)
        if organization_id:
            query = query.filter(cls.organization_id == organization_id)
        
        total = Decimal("0")
        for payment in query.all():
            total += Decimal(str(payment.amount))
        return total