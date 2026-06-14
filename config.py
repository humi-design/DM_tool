"""Configuration management for Viraly platform."""

from datetime import timedelta
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    BASE_DIR = Path(__file__).parent
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32))
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'viraly')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
    
    # Security
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
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.urandom(32))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv("REDIS_URL", "memory://")
    RATELIMIT_DEFAULT = "200 per minute"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@viraly.io")
    
    # Cache
    CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")
    CACHE_REDIS_URL = os.getenv("REDIS_URL")
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Application
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "csv"}
    
    # OAuth Providers
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "/auth/oauth/google/callback")
    
    # Meta / Instagram Business OAuth
    META_APP_ID = os.getenv("META_APP_ID")
    META_APP_SECRET = os.getenv("META_APP_SECRET")
    META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "/instagram/oauth/callback")
    META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", os.urandom(32).hex())
    META_WEBHOOK_CALLBACK_URL = os.getenv("META_WEBHOOK_CALLBACK_URL")
    
    # OTP Configuration
    OTP_ISSUER_NAME = "Viraly"
    OTP_DIGITS = 6
    OTP_INTERVAL = 300
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = BASE_DIR / "logs" / "viraly.log"
    
    # Monitoring
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    NEWRELIC_LICENSE_KEY = os.getenv("NEWRELIC_LICENSE_KEY")
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # Password hashing
    PASSWORD_HASH_METHOD = "bcrypt"
    PASSWORD_BCRYPT_ROUNDS = 12
    PASSWORD_ARGON2_MEMORY_COST = 65536
    PASSWORD_ARGON2_TIME_COST = 3
    PASSWORD_ARGON2_PARALLELISM = 4
    
    # Billing Configuration
    BILLING_PROVIDER = os.getenv("BILLING_PROVIDER", "stripe")
    
    # Stripe Configuration
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # Razorpay Configuration
    RAZORPAY_API_KEY = os.getenv("RAZORPAY_API_KEY")
    RAZORPAY_SECRET_KEY = os.getenv("RAZORPAY_SECRET_KEY")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DEV_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/viraly_dev"
    )
    SQLALCHEMY_ECHO = True
    
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
        Config.init_app(app)
        
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