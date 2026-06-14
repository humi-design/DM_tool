"""Onboarding models for storing user profile and knowledge base data."""
from datetime import datetime
from typing import Optional
from app import db


class OnboardingSession(db.Model):
    """Model for tracking onboarding sessions."""
    __tablename__ = "onboarding_sessions"

    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # creator, business, restaurant, agency, coach
    profile_type = db.Column(db.String(50), nullable=True)  # business, creator
    current_step = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile_data = db.relationship("ProfileData", backref="session", uselist=False, cascade="all, delete-orphan")
    knowledge_base = db.relationship("KnowledgeBase", backref="session", uselist=False, cascade="all, delete-orphan")
    uploaded_files = db.relationship("UploadedFile", backref="session", cascade="all, delete-orphan")
    conversation_history = db.relationship("ConversationMessage", backref="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OnboardingSession {self.id} - {self.user_type}>"


class ProfileData(db.Model):
    """Model for storing profile information collected during onboarding."""
    __tablename__ = "profile_data"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("onboarding_sessions.id"), nullable=False)
    
    # Basic info
    display_name = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    
    # Social links
    instagram = db.Column(db.String(255), nullable=True)
    twitter = db.Column(db.String(255), nullable=True)
    linkedin = db.Column(db.String(255), nullable=True)
    github = db.Column(db.String(255), nullable=True)
    youtube = db.Column(db.String(255), nullable=True)
    
    # Tags
    tags = db.Column(db.JSON, default=list)
    
    # Type-specific data stored as JSON
    type_specific_data = db.Column(db.JSON, default=dict)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProfileData {self.display_name}>"


class KnowledgeBase(db.Model):
    """Model for storing knowledge base data (FAQ, resources, etc.)."""
    __tablename__ = "knowledge_base"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("onboarding_sessions.id"), nullable=False)
    
    # FAQ items
    faqs = db.Column(db.JSON, default=list)
    
    # Resources (external links)
    resources = db.Column(db.JSON, default=list)
    
    # Additional data
    additional_info = db.Column(db.JSON, default=dict)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<KnowledgeBase {self.id}>"


class UploadedFile(db.Model):
    """Model for storing uploaded file metadata during onboarding."""
    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("onboarding_sessions.id"), nullable=False)
    
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # menu, catalog, brochure, pdf, pricing, other
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    file_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UploadedFile {self.original_filename}>"
    
    @property
    def size_formatted(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class ConversationMessage(db.Model):
    """Model for storing AI conversation history during onboarding."""
    __tablename__ = "conversation_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey("onboarding_sessions.id"), nullable=False)
    
    message_type = db.Column(db.String(20), nullable=False)  # user, ai
    content = db.Column(db.Text, nullable=False)
    extra_data = db.Column(db.JSON, default=dict)  # For storing response types, suggestions, etc.
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ConversationMessage {self.id} - {self.message_type}>"


class OnboardingTemplate(db.Model):
    """Model for storing customizable onboarding templates."""
    __tablename__ = "onboarding_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)  # creator, business, etc.
    is_default = db.Column(db.Boolean, default=False)
    
    # Template configuration
    welcome_message = db.Column(db.Text, nullable=True)
    questions = db.Column(db.JSON, default=list)
    required_fields = db.Column(db.JSON, default=list)
    optional_fields = db.Column(db.JSON, default=list)
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<OnboardingTemplate {self.name}>"