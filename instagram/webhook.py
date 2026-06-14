"""Instagram webhook module for handling Meta webhook events."""

import logging
import json
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from functools import wraps

from flask import request, current_app

from app import db
from services.instagram_service import get_instagram_service, InstagramServiceError
from repositories.instagram_repository import (
    InstagramRepository,
    WebhookLogRepository,
    EventLogRepository
)

logger = logging.getLogger(__name__)


class WebhookProcessingError(Exception):
    """Error during webhook processing."""
    
    def __init__(self, message: str, event_type: str = None, retry: bool = True):
        self.message = message
        self.event_type = event_type
        self.retry = retry
        super().__init__(self.message)


class EventHandler(ABC):
    """Abstract base class for webhook event handlers."""
    
    SUPPORTED_EVENTS: List[str] = []
    
    @abstractmethod
    def handle(self, payload: Dict[str, Any], account_id: str) -> bool:
        """Handle the event. Returns True if handled successfully."""
        pass
    
    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate the event payload structure."""
        return True


class WebhookModule:
    """Module for handling Instagram webhook events from Meta."""
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        self.register_handler(CommentsEventHandler())
        self.register_handler(MessagesEventHandler())
        self.register_handler(MentionsEventHandler())
        self.register_handler(StoryInsightsHandler())
        self.register_handler(MediaInsightsHandler())
        self.register_handler(AccountUpdatesHandler())
    
    def register_handler(self, handler: EventHandler):
        """Register an event handler."""
        for event_type in handler.SUPPORTED_EVENTS:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.info(f"Registered handler for event: {event_type}")
    
    def process_webhook(self, payload: bytes, signature: str, account_id: str = None) -> Dict[str, Any]:
        """Process an incoming webhook payload."""
        service = get_instagram_service()
        
        # Parse raw payload
        try:
            raw_payload = payload.decode("utf-8")
            data = json.loads(raw_payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse webhook payload: {str(e)}")
            raise WebhookProcessingError(f"Invalid JSON payload: {str(e)}", retry=False)
        
        # Log the webhook
        webhook_log = WebhookLogRepository.create_log(
            event_type="webhook_received",
            raw_payload=raw_payload,
            request_method=request.method,
            request_ip=request.remote_addr,
            request_user_agent=request.headers.get("User-Agent"),
            request_headers=dict(request.headers),
            webhook_url=request.url,
            instagram_account_id=account_id,
        )
        
        # Validate signature
        app_secret = current_app.config.get("META_APP_SECRET")
        if signature and not service.verify_webhook_signature(raw_payload, signature, app_secret):
            logger.warning(f"Invalid webhook signature for log {webhook_log.id}")
            WebhookLogRepository.update_log_status(
                webhook_log.id,
                "failed",
                error="Invalid signature",
                signature_valid=False,
                signature_error="Signature verification failed"
            )
            raise WebhookProcessingError("Invalid signature", retry=False)
        
        WebhookLogRepository.update_log_status(
            webhook_log.id,
            "processing",
            signature_valid=True
        )
        
        # Process entries
        results = []
        entries = data.get("entry", [])
        
        for entry in entries:
            entry_results = self._process_entry(entry, webhook_log.id)
            results.extend(entry_results)
        
        # Mark as processed
        WebhookLogRepository.mark_as_processed(webhook_log.id, success=True)
        
        return {
            "success": True,
            "webhook_log_id": webhook_log.id,
            "events_processed": len(results),
            "results": results,
        }
    
    def _process_entry(self, entry: Dict[str, Any], webhook_log_id: str) -> List[Dict[str, Any]]:
        """Process a webhook entry."""
        results = []
        account_id = entry.get("id")  # Instagram account ID from Meta
        time = entry.get("time")
        
        if isinstance(time, str):
            try:
                time = datetime.fromisoformat(time.replace("Z", "+00:00"))
            except ValueError:
                time = datetime.utcnow()
        
        changes = entry.get("changes", [])
        
        for change in changes:
            change_result = self._process_change(change, account_id, webhook_log_id, time)
            if change_result:
                results.append(change_result)
        
        return results
    
    def _process_change(self, change: Dict[str, Any], account_id: str, webhook_log_id: str, event_time: datetime) -> Optional[Dict[str, Any]]:
        """Process a webhook change event."""
        field = change.get("field")  # e.g., "comments", "messages", "mentions"
        value = change.get("value", {})
        
        # Determine event type
        if field == "comments":
            event_type = "comment"
        elif field == "messages":
            event_type = "message"
        elif field == "mentions":
            event_type = "mention"
        else:
            event_type = field
        
        # Extract event ID for idempotency
        event_id = value.get("id") or value.get("comment_id") or value.get("message_id")
        
        # Check for duplicate
        if event_id:
            # Check in event logs
            if EventLogRepository.is_duplicate(event_id):
                logger.info(f"Duplicate event detected: {event_id}")
                # Log as duplicate but don't process
                WebhookLogRepository.create_log(
                    event_type=event_type,
                    raw_payload=json.dumps(change),
                    instagram_account_id=account_id,
                    event_id=event_id,
                    webhook_url=request.url if 'request' in dir() else None,
                )
                existing_log = WebhookLogRepository.get_duplicate_by_event_id(event_id)
                if existing_log:
                    WebhookLogRepository.mark_as_duplicate(webhook_log_id, existing_log.id)
                return {"event_id": event_id, "status": "duplicate", "skipped": True}
        
        # Find account
        instagram_account = None
        if account_id:
            instagram_account = InstagramRepository.get_account_by_instagram_id(account_id)
        
        account_db_id = instagram_account.id if instagram_account else None
        
        # Create event log
        event_log = EventLogRepository.create_log(
            instagram_account_id=account_db_id,
            webhook_log_id=webhook_log_id,
            event_type=event_type,
            event_id=event_id,
            sender_id=value.get("from", {}).get("id") if isinstance(value.get("from"), dict) else value.get("from"),
            recipient_id=value.get("to", {}).get("id") if isinstance(value.get("to"), dict) else value.get("to"),
            message_id=value.get("message", {}).get("mid") if isinstance(value.get("message"), dict) else None,
            comment_id=value.get("comment_id"),
            event_data=value,
            event_time=event_time or datetime.utcnow(),
        )
        
        # Get handlers for this event type
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            logger.debug(f"No handlers registered for event type: {event_type}")
            return {"event_id": event_id, "event_type": event_type, "status": "no_handlers"}
        
        # Execute handlers
        success = True
        error_message = None
        
        for handler in handlers:
            try:
                if handler.validate_payload(value):
                    handler.handle(value, account_db_id)
                else:
                    logger.warning(f"Handler {handler.__class__.__name__} rejected payload for event {event_id}")
            except Exception as e:
                logger.error(f"Handler {handler.__class__.__name__} failed: {str(e)}")
                success = False
                error_message = str(e)
        
        # Update event log status
        EventLogRepository.update_status(
            event_log.id,
            status="processed" if success else "failed",
            error=error_message
        )
        
        return {
            "event_id": event_id,
            "event_type": event_type,
            "status": "processed" if success else "failed",
            "error": error_message,
        }


# Event Handlers

class CommentsEventHandler(EventHandler):
    """Handler for Instagram comment events."""
    
    SUPPORTED_EVENTS = ["comments", "comment"]
    
    def handle(self, payload: Dict[str, Any], account_id: str) -> bool:
        """Process comment event."""
        comment_id = payload.get("id") or payload.get("comment_id")
        media_id = payload.get("media_id")
        text = payload.get("text", "")
        username = payload.get("from", {}).get("username", "unknown")
        user_id = payload.get("from", {}).get("id")
        
        logger.info(f"Processing comment {comment_id} from {username}: {text[:50]}...")
        
        # Create or update comment in database
        from models.comment import Comment
        
        existing = Comment.query.filter_by(ig_comment_id=comment_id).first()
        if existing:
            existing.text = text
            existing.updated_at = datetime.utcnow()
            db.session.commit()
        else:
            comment = Comment(
                instagram_account_id=account_id,
                ig_comment_id=comment_id,
                ig_media_id=media_id,
                ig_user_id=user_id,
                username=username,
                text=text,
                is_managed=True,
            )
            db.session.add(comment)
            db.session.commit()
        
        return True
    
    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate comment payload."""
        return bool(payload.get("id") or payload.get("comment_id"))


class MessagesEventHandler(EventHandler):
    """Handler for Instagram Direct Message events."""
    
    SUPPORTED_EVENTS = ["messages", "message", "message_reads", "message_deliveries"]
    
    def handle(self, payload: Dict[str, Any], account_id: str) -> bool:
        """Process message event."""
        message_id = payload.get("message", {}).get("mid") if isinstance(payload.get("message"), dict) else payload.get("mid")
        sender_id = payload.get("from", {}).get("id") if isinstance(payload.get("from"), dict) else payload.get("from")
        recipient_id = payload.get("to", {}).get("id") if isinstance(payload.get("to"), dict) else payload.get("to")
        text = payload.get("message", {}).get("text") if isinstance(payload.get("message"), dict) else payload.get("text", "")
        
        logger.info(f"Processing message {message_id} from {sender_id}")
        
        # Create or update conversation
        from models.conversation import Conversation
        
        # Find existing conversation or create new
        conversation = Conversation.query.filter_by(
            instagram_account_id=account_id,
            participant_id=sender_id
        ).first()
        
        if not conversation:
            conversation = Conversation(
                instagram_account_id=account_id,
                participant_id=sender_id,
                participant_type="instagram_user",
                last_message_at=datetime.utcnow(),
            )
            db.session.add(conversation)
            db.session.commit()
        
        return True
    
    def validate_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate message payload."""
        return bool(payload.get("from"))


class MentionsEventHandler(EventHandler):
    """Handler for Instagram mention events."""
    
    SUPPORTED_EVENTS = ["mentions", "mentions"]
    
    def handle(self, payload: Dict[str, Any], account_id: str) -> bool:
        """Process mention event."""
        mention_id = payload.get("id")
        media_id = payload.get("media_id")
        username = payload.get("from", {}).get("username", "unknown")
        text = payload.get("text", "")
        
        logger.info(f"Processing mention {mention_id} from {username}")
        
        # Mentions are typically stored as a special type of comment
        from models.comment import Comment
        
        existing = Comment.query.filter_by(ig_comment_id=f"mention_{mention_id}").first()
        if not existing:
            comment = Comment(
                instagram_account_id=account_id,
                ig_comment_id=f"mention_{mention_id}",
                ig_media_id=media_id,
                username=username,
                text=f"@{text}",
                is_managed=True,
            )
            db.session.add(comment)
            db.session.commit()
        
        return True


class StoryInsightsHandler(EventHandler):
    """Handler for Instagram Story insights events."""
    
    SUPPORTED_EVENTS = ["story_insights", "story"]
    
    def handle(self, payload: Dict[str, Any], account_id: str) -> bool:
        """Process story insights event."""
        media_id = payload.get("media_id")
        impressions = payload.get("impressions", 0)
        reach = payload.get("reach", 0)
        replies = payload.get("replies", 0)
        
        logger.info(f"Processing story insights for {media_id}: {reach} reach, {impressions} impressions")
        
        # Story insights would be stored in analytics tables
        # This is a placeholder for the actual implementation
        
        return True


class MediaInsightsHandler(EventHandler):
    """Handler for Instagram Media insights events."""
    
    SUPPORTED_EVENTS = ["media_insights", "media"]
    
    def handle(self, payload: Dict[str, Any], account_id: str) -> bool:
        """Process media insights event."""
        media_id = payload.get("media_id")
        media_type = payload.get("media_type")
        
        logger.info(f"Processing media insights for {media_id}")
        
        return True


class AccountUpdatesHandler(EventHandler):
    """Handler for Instagram account update events."""
    
    SUPPORTED_EVENTS = ["account_updates", "account", "ig_business_account"]
    
    def handle(self, payload: Dict[str, Any], account_id: str) -> bool:
        """Process account update event."""
        logger.info(f"Processing account update for {account_id}")
        
        # Trigger account sync
        if account_id:
            try:
                service = get_instagram_service()
                service.sync_account(account_id)
            except Exception as e:
                logger.error(f"Failed to sync account after update: {str(e)}")
        
        return True


class WebhookRetryHandler:
    """Handler for retrying failed webhooks."""
    
    MAX_RETRIES = 4
    BACKOFF_MINUTES = [1, 5, 15, 60]
    
    @classmethod
    def process_retries(cls) -> Dict[str, Any]:
        """Process pending webhook retries."""
        service = get_instagram_service()
        failed_logs = WebhookLogRepository.get_failed_logs(limit=100)
        
        processed = 0
        failed = 0
        
        for log in failed_logs:
            if log.retry_count >= cls.MAX_RETRIES:
                logger.warning(f"Webhook log {log.id} exceeded max retries")
                continue
            
            try:
                # Re-process the webhook
                webhook_module = WebhookModule()
                
                # Parse and re-process
                data = json.loads(log.raw_payload)
                webhook_module._process_entry(data.get("entry", [{}])[0], log.id)
                
                log.mark_processed(success=True)
                db.session.commit()
                processed += 1
                
            except Exception as e:
                log.increment_retry()
                log.processing_error = str(e)
                db.session.commit()
                failed += 1
                logger.error(f"Retry failed for log {log.id}: {str(e)}")
        
        return {
            "processed": processed,
            "failed": failed,
            "remaining": len(failed_logs) - processed - failed,
        }


# Singleton instance
_webhook_module = None


def get_webhook_module() -> WebhookModule:
    """Get webhook module singleton."""
    global _webhook_module
    if _webhook_module is None:
        _webhook_module = WebhookModule()
    return _webhook_module


def process_webhook_with_retry(payload: bytes, signature: str, account_id: str = None) -> Dict[str, Any]:
    """Process webhook with automatic retry on failure."""
    webhook_module = get_webhook_module()
    
    try:
        return webhook_module.process_webhook(payload, signature, account_id)
    except WebhookProcessingError as e:
        if e.retry:
            # Log for retry
            logger.info(f"Webhook marked for retry: {e.message}")
        raise