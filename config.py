"""Configuration management for AI Social OS platform.

ONLY 2 ENV VARS ARE MANDATORY:
    DATABASE_URL            - Database connection string
    MASTER_ENCRYPTION_KEY   - Encryption key for secrets (256-bit)

ALL OTHER CONFIGS ARE OPTIONAL:
    The application boots and runs without any optional services.
    Unconfigured providers show as "not_configured" in /health endpoint.

AUTO-GENERATED IF NOT SET:
    SECRET_KEY    - Flask secret key (generated on first boot)
    JWT_SECRET    - JWT signing secret (generated on first boot)

OPTIONAL SERVICE PROVIDERS (all optional):
    AI Providers:     GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
    OAuth:            GOOGLE_CLIENT_ID, META_APP_ID, etc.
    Payments:         STRIPE_API_KEY, RAZORPAY_KEY_ID, PAYPAL_CLIENT_ID, etc.
    Email:            MAIL_USERNAME, MAIL_PASSWORD, etc.
    Cache:            REDIS_URL (defaults to in-memory)
"""

from datetime import timedelta
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _generate_secret(length: int = 32) -> str:
    """Generate a secure random secret."""
    return secrets.token_hex(length)


class Config:
    """Base configuration - all service configs are optional."""

    BASE_DIR = Path(__file__).parent
    
    # =======================================================================
    # MANDATORY: Database
    # =======================================================================
    _db_url = os.environ.get("DATABASE_URL")
    if not _db_url:
        _db_type = os.getenv("DB_TYPE", "sqlite")
        if _db_type == "postgresql":
            _db_url = f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}@" \
                      f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'ai_social_os')}"
        else:
            _db_url = "sqlite:///ai_social_os.db"
    
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Use simpler engine options for SQLite
    if "sqlite" in _db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": 10,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }
    
    # =======================================================================
    # OPTIONAL: Master encryption key (REQUIRED for production security)
    # =======================================================================
    MASTER_ENCRYPTION_KEY = os.environ.get("MASTER_ENCRYPTION_KEY")
    if not MASTER_ENCRYPTION_KEY:
        # WARNING: Using insecure default for development only
        MASTER_ENCRYPTION_KEY = "dev-only-key-not-for-production-use"
    
    # =======================================================================
    # OPTIONAL: Generated secrets (auto-generated if not set)
    # =======================================================================
    SECRET_KEY = os.environ.get("SECRET_KEY") or _generate_secret()
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET") or _generate_secret()
    
    # =======================================================================
    # Security
    # =======================================================================
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
    WTF_CSRF_FIELD_NAME = "csrf_token"
    
    # Session
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # JWT
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL", "memory://")
    RATELIMIT_DEFAULT = "200 per minute"
    RATELIMIT_HEADERS_ENABLED = True
    
    # =======================================================================
    # OPTIONAL: Mail (defaults to disabled/silent)
    # =======================================================================
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")
    MAIL_SUPPRESS_SEND = not bool(os.getenv("MAIL_USERNAME"))
    
    # =======================================================================
    # OPTIONAL: Cache
    # =======================================================================
    CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")
    CACHE_REDIS_URL = os.getenv("REDIS_URL")
    CACHE_DEFAULT_TIMEOUT = 300
    
    # =======================================================================
    # OPTIONAL: Application
    # =======================================================================
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "csv"}
    
    # =======================================================================
    # OPTIONAL: OAuth Providers (Google)
    # =======================================================================
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "/auth/oauth/google/callback")
    
    # =======================================================================
    # OPTIONAL: Meta / Instagram OAuth
    # =======================================================================
    META_APP_ID = os.getenv("META_APP_ID")
    META_APP_SECRET = os.getenv("META_APP_SECRET")
    META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "/instagram/oauth/callback")
    META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", _generate_secret())
    META_WEBHOOK_CALLBACK_URL = os.getenv("META_WEBHOOK_CALLBACK_URL")
    
    # =======================================================================
    # OPTIONAL: AI Providers
    # =======================================================================
    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Anthropic (Claude)
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    
    # Ollama (local)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # Qwen
    QWEN_API_KEY = os.getenv("QWEN_API_KEY")
    QWEN_BASE_URL = os.getenv("QWEN_BASE_URL")
    
    # Gemma
    GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
    GEMMA_BASE_URL = os.getenv("GEMMA_BASE_URL")
    
    # Mistral
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL")
    
    # =======================================================================
    # OPTIONAL: Payment Providers
    # =======================================================================
    # Stripe
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # Razorpay
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    
    # Paytm
    PAYTM_MERCHANT_ID = os.getenv("PAYTM_MERCHANT_ID")
    PAYTM_MERCHANT_KEY = os.getenv("PAYTM_MERCHANT_KEY")
    PAYTM_WEBHOOK_SECRET = os.getenv("PAYTM_WEBHOOK_SECRET")
    
    # PayPal
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
    
    # PhonePe
    PHONEPE_MERCHANT_ID = os.getenv("PHONEPE_MERCHANT_ID")
    PHONEPE_SALT_KEY = os.getenv("PHONEPE_SALT_KEY")
    PHONEPE_SALT_INDEX = os.getenv("PHONEPE_SALT_INDEX", "1")
    
    # Cashfree
    CASHFREE_CLIENT_ID = os.getenv("CASHFREE_CLIENT_ID")
    CASHFREE_CLIENT_SECRET = os.getenv("CASHFREE_CLIENT_SECRET")
    
    # =======================================================================
    # OTP Configuration
    # =======================================================================
    OTP_ISSUER_NAME = "AI Social OS"
    OTP_DIGITS = 6
    OTP_INTERVAL = 300
    
    # =======================================================================
    # Logging & Monitoring
    # =======================================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = BASE_DIR / "logs" / "ai_social_os.log"
    
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    NEWRELIC_LICENSE_KEY = os.getenv("NEWRELIC_LICENSE_KEY")
    
    # =======================================================================
    # Pagination
    # =======================================================================
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # =======================================================================
    # Password hashing
    # =======================================================================
    PASSWORD_HASH_METHOD = "bcrypt"
    PASSWORD_BCRYPT_ROUNDS = 12
    PASSWORD_ARGON2_MEMORY_COST = 65536
    PASSWORD_ARGON2_TIME_COST = 3
    PASSWORD_ARGON2_PARALLELISM = 4
    
    # =======================================================================
    # Helper methods for checking provider availability
    # =======================================================================
    @classmethod
    def has_ai_provider(cls) -> bool:
        """Check if any AI provider is configured."""
        return any([
            cls.GEMINI_API_KEY,
            cls.OPENAI_API_KEY,
            cls.ANTHROPIC_API_KEY,
            cls.OLLAMA_BASE_URL,
            cls.QWEN_API_KEY,
            cls.MISTRAL_API_KEY,
        ])
    
    @classmethod
    def has_payment_provider(cls) -> bool:
        """Check if any payment provider is configured."""
        return any([
            cls.STRIPE_API_KEY,
            cls.RAZORPAY_KEY_ID,
            cls.PAYTM_MERCHANT_ID,
            cls.PAYPAL_CLIENT_ID,
            cls.PHONEPE_MERCHANT_ID,
            cls.CASHFREE_CLIENT_ID,
        ])
    
    @classmethod
    def has_oauth_provider(cls) -> bool:
        """Check if any OAuth provider is configured."""
        return any([
            cls.GOOGLE_CLIENT_ID and cls.GOOGLE_CLIENT_SECRET,
            cls.META_APP_ID and cls.META_APP_SECRET,
        ])
    
    @classmethod
    def has_email_configured(cls) -> bool:
        """Check if email is configured."""
        return bool(cls.MAIL_USERNAME and cls.MAIL_PASSWORD)


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    # Use SQLite for local development
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DEV_DATABASE_URL",
        "sqlite:///aios.db"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SQLALCHEMY_ECHO = False
    
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    
    RATELIMIT_ENABLED = False
    
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN")
    
    PASSWORD_BCRYPT_ROUNDS = 14
    
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL")
    
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.getenv("REDIS_URL")
    
    LOG_LEVEL = "WARNING"
    
    @classmethod
    def init_app(cls, app):
        """Production initialization."""
        if cls.SENTRY_DSN:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            
            sentry_sdk.init(
                dsn=cls.SENTRY_DSN,
                integrations=[FlaskIntegration()],
                traces_sample_rate=0.1,
                environment="production",
            )
        
        if cls.NEWRELIC_LICENSE_KEY:
            import newrelic.agent
            newrelic.agent.initialize()


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    DEBUG = True
    
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    
    RATELIMIT_ENABLED = False
    CACHE_TYPE = "simple"
    
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    
    MAIL_SUPPRESS_SEND = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str = None) -> Config:
    """Get configuration based on environment."""
    env = env or os.getenv("FLASK_ENV", "development")
    return config.get(env, DevelopmentConfig)