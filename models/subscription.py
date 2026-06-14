"""Subscription model for organization billing."""

from datetime import datetime

from app import db
from models.base import BaseModel


class Subscription(BaseModel):
    """Subscription model for organization billing."""
    
    __tablename__ = "subscriptions"
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    plan_id = db.Column(db.String(100), nullable=False, index=True)
    plan_name = db.Column(db.String(100), nullable=False)
    
    status = db.Column(db.String(50), default="active", nullable=False, index=True)
    
    billing_cycle = db.Column(db.String(20), default="monthly", nullable=False, index=True)
    billing_period_start = db.Column(db.DateTime, nullable=False, index=True)
    billing_period_end = db.Column(db.DateTime, nullable=False, index=True)
    
    trial_start = db.Column(db.DateTime, nullable=True)
    trial_end = db.Column(db.DateTime, nullable=True, index=True)
    
    cancel_at_period_end = db.Column(db.Boolean, default=False, nullable=False, index=True)
    canceled_at = db.Column(db.DateTime, nullable=True, index=True)
    
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    
    external_subscription_id = db.Column(db.String(255), nullable=True, index=True)
    external_customer_id = db.Column(db.String(255), nullable=True, index=True)
    
    payment_method = db.Column(db.String(50), nullable=True)
    last_payment_at = db.Column(db.DateTime, nullable=True, index=True)
    next_payment_at = db.Column(db.DateTime, nullable=True, index=True)
    
    failed_payment_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_failed_payment_at = db.Column(db.DateTime, nullable=True)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", foreign_keys=[organization_id], back_populates="subscriptions")
    invoices = db.relationship("Invoice", foreign_keys="Invoice.subscription_id", back_populates="subscription", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("Payment", foreign_keys="Payment.subscription_id", back_populates="subscription", lazy="dynamic", cascade="all, delete-orphan")
    usage_records = db.relationship("UsageRecord", foreign_keys="UsageRecord.subscription_id", back_populates="subscription", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index("idx_sub_org_status", "organization_id", "status"),
        db.Index("idx_sub_status_period", "status", "billing_period_end"),
        db.Index("idx_sub_external", "external_subscription_id", "external_customer_id"),
        db.Index("idx_sub_next_payment", "next_payment_at", "status"),
    )
    
    STATUS_ACTIVE = "active"
    STATUS_TRIALING = "trialing"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"
    STATUS_PAUSED = "paused"
    
    BILLING_MONTHLY = "monthly"
    BILLING_ANNUAL = "annual"
    
    def to_dict(self):
        """Convert subscription to dictionary."""
        return super().to_dict()
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in (self.STATUS_ACTIVE, self.STATUS_TRIALING)
    
    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial."""
        return self.status == self.STATUS_TRIALING
    
    @property
    def is_past_due(self) -> bool:
        """Check if subscription is past due."""
        return self.status == self.STATUS_PAST_DUE
    
    def cancel(self, at_period_end: bool = True) -> None:
        """Cancel the subscription."""
        self.cancel_at_period_end = at_period_end
        if not at_period_end:
            self.status = self.STATUS_CANCELED
            self.canceled_at = datetime.utcnow()
        db.session.commit()
    
    def pause(self) -> None:
        """Pause the subscription."""
        self.status = self.STATUS_PAUSED
        db.session.commit()
    
    def resume(self) -> None:
        """Resume a paused subscription."""
        self.status = self.STATUS_ACTIVE
        db.session.commit()