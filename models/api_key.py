"""APIKey model for programmatic access."""

from datetime import datetime
import hashlib
import secrets

from app import db
from models.base import BaseModel


class APIKey(BaseModel):
    """API key model for programmatic access."""
    
    __tablename__ = "api_keys"
    
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    key_prefix = db.Column(db.String(20), nullable=False, index=True)
    key_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    
    scopes = db.Column(db.JSON, default=list, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    last_used_at = db.Column(db.DateTime, nullable=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    
    rate_limit = db.Column(db.Integer, default=1000, nullable=False)
    rate_limit_period = db.Column(db.String(20), default="minute", nullable=False)
    
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], back_populates="api_keys")
    organization = db.relationship("Organization", foreign_keys=[organization_id], back_populates="api_keys")
    
    __table_args__ = (
        db.Index("idx_api_key_org_active", "organization_id", "is_active"),
        db.Index("idx_api_key_user_active", "user_id", "is_active"),
        db.Index("idx_api_key_expires", "expires_at", "is_active"),
    )
    
    SCOPE_READ = "read"
    SCOPE_WRITE = "write"
    SCOPE_DELETE = "delete"
    SCOPE_ADMIN = "admin"
    
    @classmethod
    def generate_key(cls) -> tuple[str, str, str]:
        """Generate a new API key and return (raw_key, key_hash, prefix)."""
        raw_key = f"dm_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:20]
        return raw_key, key_hash, prefix
    
    @classmethod
    def create(
        cls,
        user_id: str,
        organization_id: str,
        name: str,
        scopes: list = None,
        expires_at: datetime = None,
        rate_limit: int = 1000,
        description: str = None,
        user_agent: str = None,
    ) -> tuple["APIKey", str]:
        """Create a new API key."""
        raw_key, key_hash, prefix = cls.generate_key()
        
        api_key = cls(
            user_id=user_id,
            organization_id=organization_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes or [cls.SCOPE_READ],
            expires_at=expires_at,
            rate_limit=rate_limit,
            description=description,
            user_agent=user_agent,
        )
        db.session.add(api_key)
        db.session.commit()
        return api_key, raw_key
    
    def verify_key(self, raw_key: str) -> bool:
        """Verify a raw API key against this key."""
        if self.is_revoked or not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return key_hash == self.key_hash
    
    def revoke(self) -> None:
        """Revoke the API key."""
        self.is_revoked = True
        self.is_active = False
        db.session.commit()
    
    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def find_by_key(cls, raw_key: str) -> "APIKey":
        """Find an API key by its raw value."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return cls.query.filter_by(key_hash=key_hash, is_active=True, is_revoked=False).first()
    
    def to_dict(self, include_key: bool = False):
        """Convert API key to dictionary."""
        data = super().to_dict()
        data.pop("key_hash", None)
        return data