"""Models package."""

from models.base import BaseModel, TimestampMixin, SoftDeleteMixin, UUIDPrimaryKeyMixin
from models.user import User
from models.organization import Organization, OrganizationMember
from models.business import Business, BusinessProfile
from models.instagram import InstagramAccount
from models.resource import Resource
from models.comment import Comment
from models.conversation import Conversation, Message
from models.lead import Lead
from models.subscription import Subscription
from models.audit_log import AuditLog
from models.api_key import APIKey
from models.report import Report
from models.setting import Setting
from models.notification import Notification
from models.auth import (
    RefreshToken,
    LoginAttempt,
    OTPCode,
    PasswordResetToken,
    EmailVerification,
    UserSession,
)
from models.onboarding import (
    OnboardingSession,
    ProfileData,
    KnowledgeBase,
    UploadedFile,
    ConversationMessage,
    OnboardingTemplate,
)

__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "UUIDPrimaryKeyMixin",
    # Core
    "User",
    "Organization",
    "OrganizationMember",
    "Business",
    "BusinessProfile",
    "InstagramAccount",
    # Content
    "Resource",
    "Comment",
    # Messaging
    "Conversation",
    "Message",
    # Sales
    "Lead",
    # Billing
    "Subscription",
    # Auth & Security
    "AuditLog",
    "APIKey",
    "RefreshToken",
    "LoginAttempt",
    "OTPCode",
    "PasswordResetToken",
    "EmailVerification",
    "UserSession",
    # Analytics
    "Report",
    # Settings
    "Setting",
    # Notifications
    "Notification",
    # Onboarding
    "OnboardingSession",
    "ProfileData",
    "KnowledgeBase",
    "UploadedFile",
    "ConversationMessage",
    "OnboardingTemplate",
]