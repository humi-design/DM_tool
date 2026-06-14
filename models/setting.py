"""Setting model for application and organization settings."""

from app import db
from models.base import BaseModel


class Setting(BaseModel):
    """Setting model for application and organization settings."""
    
    __tablename__ = "settings"
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    key = db.Column(db.String(255), nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), default="string", nullable=False)
    
    category = db.Column(db.String(50), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    
    is_encrypted = db.Column(db.Boolean, default=False, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", foreign_keys=[organization_id], back_populates="settings_rel")
    
    __table_args__ = (
        db.UniqueConstraint("organization_id", "key", name="uq_setting_org_key"),
        db.Index("idx_setting_category", "category", "organization_id"),
    )
    
    TYPE_STRING = "string"
    TYPE_INTEGER = "integer"
    TYPE_FLOAT = "float"
    TYPE_BOOLEAN = "boolean"
    TYPE_JSON = "json"
    TYPE_LIST = "list"
    
    CATEGORY_GENERAL = "general"
    CATEGORY_NOTIFICATIONS = "notifications"
    CATEGORY_INTEGRATIONS = "integrations"
    CATEGORY_SECURITY = "security"
    CATEGORY_BILLING = "billing"
    CATEGORY_API = "api"
    CATEGORY_INSTAGRAM = "instagram"
    
    def to_dict(self):
        """Convert setting to dictionary."""
        return super().to_dict()
    
    @property
    def typed_value(self):
        """Get the value with proper type conversion."""
        if self.value is None:
            return None
        
        if self.value_type == self.TYPE_INTEGER:
            return int(self.value)
        elif self.value_type == self.TYPE_FLOAT:
            return float(self.value)
        elif self.value_type == self.TYPE_BOOLEAN:
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == self.TYPE_JSON:
            import json
            return json.loads(self.value)
        elif self.value_type == self.TYPE_LIST:
            import json
            return json.loads(self.value)
        return self.value
    
    @typed_value.setter
    def typed_value(self, val):
        """Set the value with proper type conversion."""
        import json
        
        if val is None:
            self.value = None
            return
        
        if self.value_type == self.TYPE_BOOLEAN:
            self.value = str(val).lower()
        elif self.value_type in (self.TYPE_JSON, self.TYPE_LIST):
            self.value = json.dumps(val)
        else:
            self.value = str(val)
    
    @classmethod
    def get(cls, organization_id: str, key: str, default=None):
        """Get a setting value."""
        setting = cls.query.filter_by(organization_id=organization_id, key=key).first()
        if setting:
            return setting.typed_value
        return default
    
    @classmethod
    def set(cls, organization_id: str, key: str, value, value_type: str = None, **kwargs):
        """Set a setting value."""
        import json
        
        if value_type is None:
            if isinstance(value, bool):
                value_type = cls.TYPE_BOOLEAN
            elif isinstance(value, int):
                value_type = cls.TYPE_INTEGER
            elif isinstance(value, float):
                value_type = cls.TYPE_FLOAT
            elif isinstance(value, (list, dict)):
                value_type = cls.TYPE_JSON
            else:
                value_type = cls.TYPE_STRING
        
        setting = cls.query.filter_by(organization_id=organization_id, key=key).first()
        
        if setting is None:
            setting = cls(organization_id=organization_id, key=key)
            db.session.add(setting)
        
        setting.value_type = value_type
        
        if value_type == cls.TYPE_BOOLEAN:
            setting.value = str(value).lower()
        elif value_type in (cls.TYPE_JSON, cls.TYPE_LIST):
            setting.value = json.dumps(value)
        else:
            setting.value = str(value)
        
        for attr in ("category", "description", "is_encrypted", "is_public"):
            if attr in kwargs:
                setattr(setting, attr, kwargs[attr])
        
        db.session.commit()
        return setting