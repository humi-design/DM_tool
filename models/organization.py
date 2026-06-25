"""Organization model."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Organization(BaseModel, SoftDeleteMixin):
    """Organization model for multi-tenancy."""
    
    __tablename__ = "organizations"
    
    name = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    plan = db.Column(db.String(50), default="free", nullable=False, index=True)
    plan_expires_at = db.Column(db.DateTime, nullable=True, index=True)
    
    settings = db.Column(db.JSON, default=dict, nullable=False)
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    owner = db.relationship("User", foreign_keys=[owner_id], back_populates="owned_organizations", overlaps="owned_organizations")
    users = db.relationship("User", foreign_keys="User.organization_id", back_populates="organization", overlaps="organization")
    members = db.relationship("OrganizationMember", foreign_keys="OrganizationMember.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    businesses = db.relationship("Business", foreign_keys="Business.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    subscriptions = db.relationship("Subscription", foreign_keys="Subscription.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    api_keys = db.relationship("APIKey", foreign_keys="APIKey.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", foreign_keys="AuditLog.organization_id", back_populates="organization", lazy="dynamic")
    settings_rel = db.relationship("Setting", foreign_keys="Setting.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", foreign_keys="Invoice.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("Payment", foreign_keys="Payment.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    usage_records = db.relationship("UsageRecord", foreign_keys="UsageRecord.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    organization_usage = db.relationship("OrganizationUsage", foreign_keys="OrganizationUsage.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    organization_features = db.relationship("OrganizationFeature", foreign_keys="OrganizationFeature.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    
    # SaaS relationships (required by SaaS models)
    saas_overrides = db.relationship("SaaSOrganizationOverride", foreign_keys="SaaSOrganizationOverride.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    saas_usage_tracking = db.relationship("SaaSUsageTracking", foreign_keys="SaaSUsageTracking.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    saas_invoices = db.relationship("SaaSInvoice", foreign_keys="SaaSInvoice.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    saas_transactions = db.relationship("SaaSTransaction", foreign_keys="SaaSTransaction.organization_id", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index("idx_org_slug_active", "slug", "is_active"),
        db.Index("idx_org_plan_active", "plan", "is_active"),
    )
    
    def to_dict(self):
        """Convert organization to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data
    
    @property
    def is_plan_active(self) -> bool:
        """Check if the organization has an active plan."""
        if self.plan == "free":
            return True
        if not self.plan_expires_at:
            return False
        from datetime import datetime
        return self.plan_expires_at > datetime.utcnow()


class OrganizationMember(BaseModel):
    """Organization membership model."""
    
    __tablename__ = "organization_members"
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = db.Column(db.String(50), default="member", nullable=False, index=True)
    permissions = db.Column(db.JSON, default=list, nullable=False)
    
    invited_by = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at = db.Column(db.DateTime, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], back_populates="memberships")
    organization = db.relationship("Organization", foreign_keys=[organization_id], back_populates="members")
    inviter = db.relationship("User", foreign_keys=[invited_by])
    
    __table_args__ = (
        db.UniqueConstraint("user_id", "organization_id", name="uq_org_member"),
        db.Index("idx_org_member_org_role", "organization_id", "role"),
        db.Index("idx_org_member_user_active", "user_id", "is_active"),
    )
    
    def to_dict(self):
        """Convert membership to dictionary."""
        return super().to_dict()