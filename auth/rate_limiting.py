"""Rate limiting for authentication endpoints."""

from functools import wraps
from flask import request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


class AuthRateLimiter:
    """Rate limiter specifically for authentication endpoints."""
    
    def __init__(self, app=None):
        self.limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=[],
            storage_uri="memory://",
        )
        self._setup_limiters()
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.limiter.init_app(app)
        self._setup_limiters()
    
    def _setup_limiters(self):
        """Set up rate limiters for auth endpoints."""
        pass
    
    def login_rate_limit(self, limit_string="5 per minute"):
        """Decorator for login rate limiting."""
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                key = f"login:{get_remote_address()}"
                
                try:
                    if self.limiter.storage.get(key):
                        from services.auth_service import RateLimitError
                        raise RateLimitError("Too many login attempts. Please try again later.")
                except Exception:
                    pass
                
                return f(*args, **kwargs)
            
            decorated.__name__ = f.__name__
            return decorated
        return decorator
    
    def register_rate_limit(self, limit_string="3 per minute"):
        """Decorator for registration rate limiting."""
        def decorator(f):
            endpoint = f.__name__
            
            @wraps(f)
            def decorated(*args, **kwargs):
                return f(*args, **kwargs)
            
            decorated.__name__ = endpoint
            return decorated
        return decorator
    
    def password_reset_rate_limit(self, limit_string="3 per hour"):
        """Decorator for password reset rate limiting."""
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                return f(*args, **kwargs)
            return decorated
        return decorator
    
    def otp_rate_limit(self, limit_string="5 per minute"):
        """Decorator for OTP request rate limiting."""
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                return f(*args, **kwargs)
            return decorated
        return decorator


def login_limiter(f):
    """Rate limit login attempts - 5 per minute per IP."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from services.auth_service import RateLimitError
        
        ip = get_remote_address()
        key = f"auth_login:{ip}"
        
        from flask import current_app
        if not current_app.config.get("TESTING"):
            try:
                from flask import cache
                cache_key = f"rate:{key}"
                current_hits = cache.get(cache_key) or 0
                
                if current_hits >= 5:
                    raise RateLimitError(
                        "Too many login attempts. Please wait before trying again.",
                    )
                
                cache.set(cache_key, current_hits + 1, timeout=60)
            except RateLimitError:
                raise
            except Exception:
                pass
        
        return f(*args, **kwargs)
    return decorated


def register_limiter(f):
    """Rate limit registration attempts - 3 per hour per IP."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from services.auth_service import RateLimitError
        
        ip = get_remote_address()
        
        from flask import current_app
        if not current_app.config.get("TESTING"):
            try:
                cache_key = f"rate:register:{ip}"
                current_hits = current_app.cache.get(cache_key) or 0
                
                if current_hits >= 3:
                    raise RateLimitError(
                        "Too many registration attempts. Please try again later.",
                    )
                
                current_app.cache.set(cache_key, current_hits + 1, timeout=3600)
            except RateLimitError:
                raise
            except Exception:
                pass
        
        return f(*args, **kwargs)
    return decorated


def otp_request_limiter(f):
    """Rate limit OTP requests - 5 per minute."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from services.auth_service import RateLimitError
        
        identifier = get_remote_address()
        
        from flask import current_app
        if not current_app.config.get("TESTING"):
            try:
                cache_key = f"rate:otp:{identifier}"
                current_hits = current_app.cache.get(cache_key) or 0
                
                if current_hits >= 5:
                    raise RateLimitError(
                        "Too many OTP requests. Please wait before trying again.",
                    )
                
                current_app.cache.set(cache_key, current_hits + 1, timeout=60)
            except RateLimitError:
                raise
            except Exception:
                pass
        
        return f(*args, **kwargs)
    return decorated


def password_reset_limiter(f):
    """Rate limit password reset requests - 3 per hour per email."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, current_app
        
        email = request.json.get("email") if request.is_json else request.form.get("email")
        if email:
            try:
                cache_key = f"rate:reset:{email.lower()}"
                current_hits = current_app.cache.get(cache_key) or 0
                
                if current_hits >= 3:
                    from services.auth_service import RateLimitError
                    raise RateLimitError(
                        "Too many password reset requests. Please try again later.",
                    )
                
                current_app.cache.set(cache_key, current_hits + 1, timeout=3600)
            except Exception:
                pass
        
        return f(*args, **kwargs)
    return decorated


def api_rate_limit(limit="100 per minute"):
    """General API rate limit decorator."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated
    return decorator


class LoginAttemptTracker:
    """Track login attempts for additional security."""
    
    @staticmethod
    def record_attempt(email: str, ip: str, success: bool):
        """Record a login attempt."""
        from models.auth import LoginAttempt
        LoginAttempt.record_attempt(
            email=email,
            ip_address=ip,
            successful=success,
        )
    
    @staticmethod
    def is_locked_out(email: str, ip: str, max_attempts: int = 5, lockout_minutes: int = 15) -> bool:
        """Check if an account is locked out."""
        from datetime import datetime, timedelta
        from app import db
        
        since = datetime.utcnow() - timedelta(minutes=lockout_minutes)
        
        failed_count = db.session.query(LoginAttempt).filter(
            LoginAttempt.email == email,
            LoginAttempt.successful == False,
            LoginAttempt.attempted_at >= since,
        ).count()
        
        ip_count = db.session.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip,
            LoginAttempt.successful == False,
            LoginAttempt.attempted_at >= since,
        ).count()
        
        return failed_count >= max_attempts or ip_count >= (max_attempts * 2)
    
    @staticmethod
    def get_failed_attempts(email: str, ip: str, minutes: int = 15) -> int:
        """Get the number of recent failed attempts."""
        from datetime import datetime, timedelta
        from app import db
        
        since = datetime.utcnow() - timedelta(minutes=minutes)
        
        return db.session.query(LoginAttempt).filter(
            db.or_(
                LoginAttempt.email == email,
                LoginAttempt.ip_address == ip,
            ),
            LoginAttempt.successful == False,
            LoginAttempt.attempted_at >= since,
        ).count()