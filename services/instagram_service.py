"""Instagram service for Meta Graph API integration."""

import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from functools import wraps
import json
import inspect

import requests
from flask import current_app

from app import db
from repositories.instagram_repository import InstagramRepository, WebhookLogRepository, EventLogRepository

logger = logging.getLogger(__name__)


class InstagramServiceError(Exception):
    """Base exception for Instagram service errors."""
    
    def __init__(self, message: str, code: str = None, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class TokenExpiredError(InstagramServiceError):
    """Token has expired."""
    
    def __init__(self, message: str = "Access token has expired"):
        super().__init__(message, code="token_expired", status_code=401)


class AuthenticationError(InstagramServiceError):
    """Authentication failed."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="auth_failed", status_code=401)


class APIError(InstagramServiceError):
    """Meta API error."""
    
    def __init__(self, message: str, code: str = None, status_code: int = 500):
        super().__init__(message, code=code, status_code=status_code)


def audit_log(action: str, resource_type: str = "instagram_account"):
    """Decorator for audit logging of Instagram operations."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            start_time = datetime.utcnow()
            account_id = None
            success = False
            error_message = None
            
            # Extract account_id from args if available
            if args:
                if len(args) > 1 and isinstance(args[1], str):
                    account_id = args[1]
                elif 'account_id' in kwargs:
                    account_id = kwargs['account_id']
            
            try:
                result = f(*args, **kwargs)
                success = True
                
                # Extract account_id from result if available
                if isinstance(result, dict) and 'account' in result:
                    account_id = result['account'].get('id') if isinstance(result['account'], dict) else result['account']
                
                return result
            except Exception as e:
                error_message = str(e)
                raise
            finally:
                # Log the operation
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                _log_audit_event(
                    action=action,
                    resource_type=resource_type,
                    resource_id=account_id,
                    success=success,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )
        
        return decorated
    return decorator


def _log_audit_event(
    action: str,
    resource_type: str,
    resource_id: str = None,
    success: bool = True,
    duration_ms: int = 0,
    error_message: str = None,
    metadata: Dict[str, Any] = None
):
    """Log an audit event for Instagram operations."""
    try:
        from models.audit_log import AuditLog
        from flask import g, request
        
        # Get request context
        user_id = None
        ip_address = None
        
        try:
            if hasattr(g, 'user_id'):
                user_id = g.user_id
            if hasattr(g, 'client_ip'):
                ip_address = g.client_ip
            if not ip_address and request:
                ip_address = request.remote_addr
            if hasattr(g, 'request_id'):
                request_id = g.request_id
            else:
                request_id = None
        except RuntimeError:
            pass  # Outside request context
        
        status = "success" if success else "failure"
        
        # Create audit log entry using the model's log method
        AuditLog.log(
            action=action,
            category=AuditLog.CATEGORY_INSTAGRAM,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            status=status,
            error_message=error_message,
            new_values=metadata,
            request_id=request_id,
        )
        
        logger.info(
            f"AUDIT: {action} on {resource_type} ({resource_id}) - "
            f"success={success}, duration={duration_ms}ms"
        )
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")


class InstagramService:
    """Service for Instagram/Meta Graph API operations."""
    
    # Meta Graph API Base URLs
    META_GRAPH_URL = "https://graph.facebook.com/v18.0"
    META_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    META_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    META_DEBUG_URL = "https://graph.facebook.com/v18.0/debug_token"
    
    # Required permissions for Instagram Business
    REQUIRED_PERMISSIONS = [
        "instagram_basic",
        "instagram_content_publish",
        "instagram_manage_comments",
        "instagram_manage_insights",
        "pages_read_engagement",
        "pages_manage_metadata",
        "pages_show_list",
    ]
    
    def __init__(self, app=None):
        self.app = app
        self._app_id = None
        self._app_secret = None
        self._redirect_uri = None
        self._webhook_verify_token = None
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        self._app_id = app.config.get("META_APP_ID")
        self._app_secret = app.config.get("META_APP_SECRET")
        self._redirect_uri = app.config.get("META_REDIRECT_URI")
        self._webhook_verify_token = app.config.get("META_WEBHOOK_VERIFY_TOKEN")
    
    @property
    def app_id(self) -> str:
        if not self._app_id:
            self._app_id = self.app.config.get("META_APP_ID") if self.app else current_app.config.get("META_APP_ID")
        return self._app_id
    
    @property
    def app_secret(self) -> str:
        if not self._app_secret:
            self._app_secret = self.app.config.get("META_APP_SECRET") if self.app else current_app.config.get("META_APP_SECRET")
        return self._app_secret
    
    @property
    def redirect_uri(self) -> str:
        if not self._redirect_uri:
            self._redirect_uri = self.app.config.get("META_REDIRECT_URI") if self.app else current_app.config.get("META_REDIRECT_URI")
        return self._redirect_uri
    
    @property
    def webhook_verify_token(self) -> str:
        if not self._webhook_verify_token:
            self._webhook_verify_token = self.app.config.get("META_WEBHOOK_VERIFY_TOKEN") if self.app else current_app.config.get("META_WEBHOOK_VERIFY_TOKEN")
        return self._webhook_verify_token
    
    def get_authorization_url(self, business_id: str, state: str = None) -> str:
        """Generate Meta OAuth authorization URL."""
        import secrets
        state = state or secrets.token_urlsafe(32)
        state_data = json.dumps({"business_id": business_id, "nonce": state})
        import base64
        state_encoded = base64.urlsafe_b64encode(state_data.encode()).decode()
        
        scope = ",".join(self.REQUIRED_PERMISSIONS)
        
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "state": state_encoded,
            "response_type": "code",
        }
        
        query = "&".join([f"{k}={requests.utils.quote(v)}" for k, v in params.items()])
        return f"{self.META_AUTH_URL}?{query}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        url = self.META_TOKEN_URL
        
        data = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": self.redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        }
        
        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise AuthenticationError(f"Failed to exchange code for token: {str(e)}")
    
    def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """Convert short-lived token to long-lived token."""
        url = self.META_TOKEN_URL
        
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token,
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token conversion failed: {str(e)}")
            raise AuthenticationError(f"Failed to get long-lived token: {str(e)}")
    
    def debug_token(self, access_token: str) -> Dict[str, Any]:
        """Debug an access token."""
        params = {
            "input_token": access_token,
            "access_token": f"{self.app_id}|{self.app_secret}",
        }
        
        try:
            response = requests.get(self.META_DEBUG_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token debug failed: {str(e)}")
            raise APIError(f"Failed to debug token: {str(e)}")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token."""
        url = self.META_TOKEN_URL
        
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": refresh_token,
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError(f"Failed to refresh token: {str(e)}")
    
    def get_facebook_pages(self, access_token: str) -> List[Dict[str, Any]]:
        """Get Facebook Pages associated with the user."""
        url = f"{self.META_GRAPH_URL}/me/accounts"
        
        params = {
            "access_token": access_token,
            "fields": "id,name,category,followers_count,fan_count,about, picture",
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.RequestException as e:
            logger.error(f"Failed to get Facebook pages: {str(e)}")
            raise APIError(f"Failed to get Facebook pages: {str(e)}")
    
    def get_page_access_token(self, page_id: str, user_access_token: str) -> str:
        """Get page access token from user access token."""
        url = f"{self.META_GRAPH_URL}/{page_id}"
        
        params = {
            "fields": "access_token",
            "access_token": user_access_token,
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
        except requests.RequestException as e:
            logger.error(f"Failed to get page token: {str(e)}")
            raise APIError(f"Failed to get page token: {str(e)}")
    
    def get_instagram_business_account(self, page_access_token: str) -> Dict[str, Any]:
        """Get Instagram Business account linked to a Facebook Page."""
        url = f"{self.META_GRAPH_URL}/me/accounts"
        
        params = {
            "access_token": page_access_token,
            "fields": "instagram_business_account{id,username,name,biography,profile_picture_url,followers_count,follows_count,media_count,website,ig_id}",
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data"):
                page_data = data["data"][0]
                ig_account = page_data.get("instagram_business_account")
                if ig_account:
                    return {
                        "instagram_account": ig_account,
                        "facebook_page_id": page_data.get("id"),
                        "facebook_page_name": page_data.get("name"),
                    }
            
            raise APIError("No Instagram Business account found", code="no_ig_account", status_code=404)
        except requests.RequestException as e:
            logger.error(f"Failed to get Instagram account: {str(e)}")
            raise APIError(f"Failed to get Instagram account: {str(e)}")
    
    def get_instagram_account_info(self, instagram_user_id: str, access_token: str) -> Dict[str, Any]:
        """Get Instagram account information."""
        url = f"{self.META_GRAPH_URL}/{instagram_user_id}"
        
        params = {
            "access_token": access_token,
            "fields": "id,username,name,biography,profile_picture_url,followers_count,follows_count,media_count,website,ig_id,account_type,media_type",
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get account info: {str(e)}")
            raise APIError(f"Failed to get account info: {str(e)}")
    
    def connect_account(
        self,
        business_id: str,
        code: str
    ) -> Dict[str, Any]:
        """Complete OAuth flow and connect Instagram account."""
        # Exchange code for token
        token_response = self.exchange_code_for_token(code)
        short_lived_token = token_response.get("access_token")
        
        if not short_lived_token:
            raise AuthenticationError("No access token received")
        
        # Get long-lived token
        long_lived_response = self.get_long_lived_token(short_lived_token)
        access_token = long_lived_response.get("access_token")
        expires_in = long_lived_response.get("expires_in", 5184000)  # 60 days default
        
        # Get Meta user ID
        debug_info = self.debug_token(access_token)
        data = debug_info.get("data", {})
        meta_user_id = data.get("user_id")
        
        if not meta_user_id:
            raise AuthenticationError("Could not determine Meta user ID")
        
        # Get Facebook Pages
        pages = self.get_facebook_pages(access_token)
        
        if not pages:
            raise APIError("No Facebook Pages found", code="no_pages", status_code=400)
        
        # For now, use the first page with an Instagram account
        for page in pages:
            page_id = page.get("id")
            page_token = page.get("access_token")
            
            try:
                ig_data = self.get_instagram_business_account(page_token)
                instagram_account = ig_data.get("instagram_account", {})
                
                if instagram_account:
                    # Create or update account
                    existing = InstagramRepository.get_account_by_instagram_id(
                        instagram_account.get("id")
                    )
                    
                    token_expires = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    if existing:
                        # Update existing account
                        InstagramRepository.update_token(
                            existing.id,
                            access_token=access_token,
                            token_expires_at=token_expires,
                            facebook_page_id=page_id,
                            meta_user_id=meta_user_id,
                        )
                        account = existing
                    else:
                        # Create new account
                        account = InstagramRepository.create_account(
                            business_id=business_id,
                            instagram_user_id=instagram_account.get("id"),
                            username=instagram_account.get("username"),
                            access_token=access_token,
                            facebook_page_id=page_id,
                            meta_user_id=meta_user_id,
                            token_expires_at=token_expires,
                            full_name=instagram_account.get("name"),
                            biography=instagram_account.get("biography"),
                            profile_picture_url=instagram_account.get("profile_picture_url"),
                            followers_count=instagram_account.get("followers_count", 0),
                            following_count=instagram_account.get("follows_count", 0),
                            media_count=instagram_account.get("media_count", 0),
                            is_business=True,
                            is_connected=True,
                        )
                    
                    return {
                        "account": account.to_dict(),
                        "facebook_page": {
                            "id": page_id,
                            "name": page.get("name"),
                        },
                        "instagram_account": instagram_account,
                    }
            except Exception as e:
                logger.warning(f"Page {page_id} has no Instagram Business account: {str(e)}")
                continue
        
        raise APIError(
            "No Instagram Business account found on your Facebook Pages",
            code="no_ig_business",
            status_code=404
        )
    
    def disconnect_account(self, account_id: str) -> bool:
        """Disconnect an Instagram account."""
        account = InstagramRepository.get_account_by_id(account_id)
        if not account:
            raise APIError("Account not found", code="not_found", status_code=404)
        
        InstagramRepository.disconnect_account(account_id)
        return True
    
    def reconnect_account(self, account_id: str, code: str) -> Dict[str, Any]:
        """Reconnect a previously disconnected account."""
        account = InstagramRepository.get_account_by_id(account_id)
        if not account:
            raise APIError("Account not found", code="not_found", status_code=404)
        
        # Complete new OAuth flow
        return self.connect_account(account.business_id, code)
    
    def get_connection_status(self, account_id: str) -> Dict[str, Any]:
        """Get connection status for an account."""
        account = InstagramRepository.get_account_by_id(account_id)
        if not account:
            raise APIError("Account not found", code="not_found", status_code=404)
        
        status = {
            "connected": account.is_connected,
            "token_expired": account.is_token_expired(),
            "needs_refresh": account.needs_token_refresh(),
            "last_activity": account.last_activity_at.isoformat() if account.last_activity_at else None,
            "connected_at": account.connected_at.isoformat() if account.connected_at else None,
        }
        
        # Validate token with Meta
        try:
            debug_info = self.debug_token(account.access_token)
            data = debug_info.get("data", {})
            status["token_valid"] = data.get("is_valid", False)
            status["token_scopes"] = data.get("scopes", [])
            status["token_expires_at"] = data.get("expires_at")
            status["token_error"] = data.get("error", {}).get("message")
        except Exception as e:
            logger.warning(f"Token validation failed: {str(e)}")
            status["token_valid"] = False
            status["token_error"] = str(e)
        
        return status
    
    def sync_account(self, account_id: str) -> Dict[str, Any]:
        """Sync account data from Meta API."""
        account = InstagramRepository.get_account_by_id(account_id)
        if not account:
            raise APIError("Account not found", code="not_found", status_code=404)
        
        if not account.access_token:
            raise AuthenticationError("No access token available")
        
        # Refresh token if needed
        if account.needs_token_refresh() and account.refresh_token:
            try:
                new_token = self.refresh_token(account.refresh_token)
                InstagramRepository.update_token(
                    account_id,
                    access_token=new_token.get("access_token"),
                    token_expires_at=datetime.utcnow() + timedelta(seconds=new_token.get("expires_in", 5184000))
                )
                account.refresh()
            except Exception as e:
                logger.warning(f"Token refresh failed: {str(e)}")
        
        # Get fresh account info
        info = self.get_instagram_account_info(
            account.instagram_user_id,
            account.access_token
        )
        
        # Update account data
        InstagramRepository.update_account(
            account_id,
            username=info.get("username"),
            full_name=info.get("name"),
            biography=info.get("biography"),
            profile_picture_url=info.get("profile_picture_url"),
            followers_count=info.get("followers_count", 0),
            following_count=info.get("follows_count", 0),
            media_count=info.get("media_count", 0),
            last_synced_at=datetime.utcnow(),
        )
        
        return info
    
    def ensure_token_valid(self, account_id: str) -> str:
        """Ensure account has a valid access token."""
        account = InstagramRepository.get_account_by_id(account_id)
        if not account:
            raise APIError("Account not found", code="not_found", status_code=404)
        
        if not account.access_token:
            raise AuthenticationError("No access token available")
        
        if account.is_token_expired():
            raise TokenExpiredError()
        
        if account.needs_token_refresh() and account.refresh_token:
            try:
                new_token = self.refresh_token(account.refresh_token)
                InstagramRepository.update_token(
                    account_id,
                    access_token=new_token.get("access_token"),
                    token_expires_at=datetime.utcnow() + timedelta(seconds=new_token.get("expires_in", 5184000))
                )
                return new_token.get("access_token")
            except Exception as e:
                logger.warning(f"Token refresh failed: {str(e)}")
        
        return account.access_token
    
    def verify_webhook_signature(self, payload: str, signature: str, secret: str = None) -> bool:
        """Verify webhook signature from Meta."""
        if not signature:
            return False
        
        if secret is None:
            secret = self.app_secret
        
        # Parse signature header
        # Format: "sha256={signature}"
        parts = signature.split("sha256=")
        if len(parts) != 2:
            return False
        
        expected_signature = parts[1]
        
        # Calculate HMAC
        expected = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(expected_signature, expected)
    
    def verify_webhook_mode(self, mode: str, token: str, challenge: str) -> bool:
        """Verify webhook setup mode (hub.mode, hub.verify_token, hub.challenge)."""
        return mode == "subscribe" and token == self.webhook_verify_token


class InstagramServiceInstance:
    """Singleton instance holder."""
    _instance = None
    
    @classmethod
    def get_instance(cls) -> InstagramService:
        if cls._instance is None:
            cls._instance = InstagramService()
        return cls._instance


def get_instagram_service() -> InstagramService:
    """Get Instagram service instance."""
    return InstagramServiceInstance.get_instance()


def require_connected_account(f):
    """Decorator to require a connected Instagram account."""
    @wraps(f)
    def decorated_function(account_id, *args, **kwargs):
        account = InstagramRepository.get_account_by_id(account_id)
        if not account:
            raise APIError("Account not found", code="not_found", status_code=404)
        if not account.is_connected:
            raise APIError("Account is disconnected", code="not_connected", status_code=400)
        return f(account_id, *args, **kwargs)
    return decorated_function


def require_valid_token(f):
    """Decorator to require a valid access token."""
    @wraps(f)
    def decorated_function(account_id, *args, **kwargs):
        service = get_instagram_service()
        try:
            service.ensure_token_valid(account_id)
        except TokenExpiredError:
            raise APIError("Access token expired", code="token_expired", status_code=401)
        return f(account_id, *args, **kwargs)
    return decorated_function