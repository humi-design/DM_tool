"""Invoice model for billing invoices."""

from datetime import datetime
from decimal import Decimal

from app import db
from models.base import BaseModel


class Invoice(BaseModel):
    """Invoice model for billing."""
    
    __tablename__ = "invoices"
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    subscription_id = db.Column(
        db.String(36),
        db.ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Invoice identification
    invoice_number = db.Column(db.String(50), nullable=False, unique=True, index=True)
    external_invoice_id = db.Column(db.String(255), nullable=True, index=True)
    
    # Status and type
    status = db.Column(db.String(50), default="draft", nullable=False, index=True)
    invoice_type = db.Column(db.String(50), default="subscription", nullable=False, index=True)
    
    # Billing period
    period_start = db.Column(db.DateTime, nullable=False, index=True)
    period_end = db.Column(db.DateTime, nullable=False, index=True)
    due_date = db.Column(db.DateTime, nullable=False, index=True)
    paid_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Amounts
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    
    # Line items
    line_items = db.Column(db.JSON, default=list, nullable=False)
    
    # Payment info
    payment_method = db.Column(db.String(50), nullable=True)
    payment_reference = db.Column(db.String(255), nullable=True)
    payment_gateway = db.Column(db.String(50), nullable=True)
    
    # Customer info
    customer_name = db.Column(db.String(255), nullable=True)
    customer_email = db.Column(db.String(255), nullable=True)
    billing_address = db.Column(db.JSON, default=dict, nullable=False)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)
    
    # PDF and metadata
    pdf_url = db.Column(db.String(500), nullable=True)
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", back_populates="invoices")
    subscription = db.relationship("Subscription", back_populates="invoices")
    payments = db.relationship("Payment", back_populates="invoice", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index("idx_invoice_org_status", "organization_id", "status"),
        db.Index("idx_invoice_status_due", "status", "due_date"),
        db.Index("idx_invoice_period", "period_start", "period_end"),
    )
    
    # Status constants
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"
    STATUS_VOID = "void"
    STATUS_REFUNDED = "refunded"
    STATUS_CANCELED = "canceled"
    
    # Type constants
    TYPE_SUBSCRIPTION = "subscription"
    TYPE_USAGE = "usage"
    TYPE_ADDON = "addon"
    TYPE_ONE_TIME = "one_time"
    TYPE_CREDIT = "credit"
    
    def to_dict(self, include_organization: bool = False):
        """Convert invoice to dictionary."""
        data = super().to_dict()
        if include_organization and self.organization:
            data["organization"] = self.organization.to_dict()
        return data
    
    @property
    def is_paid(self) -> bool:
        """Check if invoice is paid."""
        return self.status == self.STATUS_PAID
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return self.status == self.STATUS_OVERDUE or (
            self.status == self.STATUS_PENDING and 
            datetime.utcnow() > self.due_date
        )
    
    @property
    def days_until_due(self) -> int:
        """Calculate days until due date."""
        if self.is_paid:
            return 0
        delta = self.due_date - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def amount_due(self) -> Decimal:
        """Get amount still due."""
        paid = sum(Decimal(str(p.amount)) for p in self.payments.filter_by(status="succeeded"))
        return Decimal(str(self.total_amount)) - paid
    
    def mark_paid(self, payment_method: str = None, payment_reference: str = None) -> None:
        """Mark invoice as paid."""
        self.status = self.STATUS_PAID
        self.paid_at = datetime.utcnow()
        if payment_method:
            self.payment_method = payment_method
        if payment_reference:
            self.payment_reference = payment_reference
        db.session.commit()
    
    def mark_overdue(self) -> None:
        """Mark invoice as overdue."""
        if self.status == self.STATUS_PENDING:
            self.status = self.STATUS_OVERDUE
            db.session.commit()
    
    def void(self, reason: str = None) -> None:
        """Void the invoice."""
        self.status = self.STATUS_VOID
        if reason:
            self.notes = (self.notes or "") + f"\nVoided: {reason}"
        db.session.commit()
    
    @classmethod
    def generate_invoice_number(cls, organization_id: str) -> str:
        """Generate unique invoice number."""
        from datetime import datetime
        prefix = f"INV-{datetime.utcnow().strftime('%Y%m')}"
        count = cls.query.filter(
            cls.organization_id == organization_id,
            cls.invoice_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{str(count + 1).zfill(4)}"
    
    @classmethod
    def get_pending_for_organization(cls, organization_id: str):
        """Get pending invoices for organization."""
        return cls.query.filter(
            cls.organization_id == organization_id,
            cls.status.in_([cls.STATUS_PENDING, cls.STATUS_OVERDUE])
        ).order_by(cls.due_date).all()
    
    @classmethod
    def get_overdue_invoices(cls):
        """Get all overdue invoices."""
        return cls.query.filter(
            cls.status == cls.STATUS_PENDING,
            cls.due_date < datetime.utcnow()
        ).all()