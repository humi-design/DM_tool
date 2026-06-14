"""User model."""

from datetime import datetime
import uuid

from argon2 import PasswordHasher
from flask_login import UserMixin

from app import db, login_manager

ph = PasswordHasher()


class User(BaseModel, UserMixin):
    """User model."""
    
    __tablename__ = "users"
    
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    
    email_verified_at = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=True)
    
    settings = db.Column(db.JSON, default=dict, nullable=False)
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = ph.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify the user's password."""
        if not self.password_hash:
            return False
        try:
            return ph.verify(self.password_hash, password)
        except Exception:
            return False
    
    def update_last_login(self, ip_address: str = None) -> None:
        """Update last login timestamp and IP."""
        self.last_login_at = datetime.utcnow()
        if ip_address:
            self.last_login_ip = ip_address
        db.session.commit()
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or self.email
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return True
    
    @property
    def is_anonymous(self) -> bool:
        """Check if user is anonymous."""
        return False
    
    def to_dict(self, include_sensitive: bool = False):
        """Convert user to dictionary."""
        data = super().to_dict()
        if not include_sensitive:
            data.pop("password_hash", None)
        data["full_name"] = self.full_name
        return data


@login_manager.user_loader
def load_user(user_id: str) -> User:
    """Load user by ID for Flask-Login."""
    return User.query.filter_by(id=user_id, is_active=True).first()