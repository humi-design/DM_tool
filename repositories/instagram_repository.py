"""Instagram repository for database operations."""

from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from app import db
from models.instagram import InstagramAccount, WebhookLog, EventLog


class InstagramRepository:
    """Repository for Instagram account database operations."""
    
    @staticmethod
    def create_account(
        business_id: str,
        instagram_user_id: str,
        username: str,
        access_token: str,
        facebook_page_id: str = None,
        meta_user_id: str = None,
        token_expires_at: datetime = None,
        token_scope: str = None,
        **kwargs
    ) -> InstagramAccount:
        """Create a new Instagram account."""
        account = InstagramAccount(
            business_id=business_id,
            instagram_user_id=instagram_user_id,
            username=username,
            access_token=access_token,
            facebook_page_id=facebook_page_id,
            meta_user_id=meta_user_id,
            token_expires_at=token_expires_at,
            token_scope=token_scope,
            connected_at=datetime.utcnow(),
            **kwargs
        )
        db.session.add(account)
        db.session.commit()
        return account
    
    @staticmethod
    def get_account_by_id(account_id: str) -> Optional[InstagramAccount]:
        """Get account by ID."""
        return InstagramAccount.query.filter_by(id=account_id, is_deleted=False).first()
    
    @staticmethod
    def get_account_by_instagram_id(instagram_user_id: str) -> Optional[InstagramAccount]:
        """Get account by Instagram user ID."""
        return InstagramAccount.query.filter_by(
            instagram_user_id=instagram_user_id,
            is_deleted=False
        ).first()
    
    @staticmethod
    def get_accounts_by_business(business_id: str) -> List[InstagramAccount]:
        """Get all Instagram accounts for a business."""
        return InstagramAccount.query.filter_by(
            business_id=business_id,
            is_deleted=False,
            is_active=True
        ).all()
    
    @staticmethod
    def get_connected_accounts() -> List[InstagramAccount]:
        """Get all connected Instagram accounts."""
        return InstagramAccount.query.filter_by(
            is_connected=True,
            is_deleted=False,
            is_active=True
        ).all()
    
    @staticmethod
    def update_account(
        account_id: str,
        **kwargs
    ) -> Optional[InstagramAccount]:
        """Update Instagram account fields."""
        account = InstagramAccountRepository.get_account_by_id(account_id)
        if not account:
            return None
        
        # Handle token updates
        if 'access_token' in kwargs:
            kwargs['last_activity_at'] = datetime.utcnow()
        
        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        db.session.commit()
        return account
    
    @staticmethod
    def update_token(
        account_id: str,
        access_token: str,
        token_expires_at: datetime = None,
        refresh_token: str = None,
        token_scope: str = None
    ) -> Optional[InstagramAccount]:
        """Update account token."""
        account = InstagramAccountRepository.get_account_by_id(account_id)
        if not account:
            return None
        
        account.access_token = access_token
        account.last_activity_at = datetime.utcnow()
        
        if token_expires_at:
            account.token_expires_at = token_expires_at
        if refresh_token:
            account.refresh_token = refresh_token
        if token_scope:
            account.token_scope = token_scope
        
        db.session.commit()
        return account
    
    @staticmethod
    def disconnect_account(account_id: str) -> Optional[InstagramAccount]:
        """Disconnect an Instagram account."""
        account = InstagramAccountRepository.get_account_by_id(account_id)
        if not account:
            return None
        
        account.is_connected = False
        account.last_activity_at = datetime.utcnow()
        db.session.commit()
        return account
    
    @staticmethod
    def reconnect_account(account_id: str, access_token: str) -> Optional[InstagramAccount]:
        """Reconnect a previously disconnected account."""
        account = InstagramAccountRepository.get_account_by_id(account_id)
        if not account:
            return None
        
        account.is_connected = True
        account.access_token = access_token
        account.last_activity_at = datetime.utcnow()
        db.session.commit()
        return account
    
    @staticmethod
    def soft_delete_account(account_id: str) -> Optional[InstagramAccount]:
        """Soft delete an Instagram account."""
        account = InstagramAccountRepository.get_account_by_id(account_id)
        if not account:
            return None
        
        account.soft_delete()
        return account
    
    @staticmethod
    def get_accounts_needing_refresh() -> List[InstagramAccount]:
        """Get accounts with tokens needing refresh."""
        accounts = InstagramAccount.query.filter_by(
            is_connected=True,
            is_deleted=False,
            is_active=True
        ).all()
        
        return [acc for acc in accounts if acc.needs_token_refresh()]
    
    @staticmethod
    def get_accounts_by_page_id(facebook_page_id: str) -> List[InstagramAccount]:
        """Get Instagram accounts linked to a Facebook Page."""
        return InstagramAccount.query.filter_by(
            facebook_page_id=facebook_page_id,
            is_deleted=False
        ).all()


class WebhookLogRepository:
    """Repository for webhook log database operations."""
    
    @staticmethod
    def create_log(
        event_type: str,
        raw_payload: str,
        request_method: str = "POST",
        request_ip: str = None,
        request_user_agent: str = None,
        request_headers: dict = None,
        webhook_url: str = None,
        event_id: str = None,
        **kwargs
    ) -> WebhookLog:
        """Create a new webhook log entry."""
        log = WebhookLog(
            event_type=event_type,
            raw_payload=raw_payload,
            request_method=request_method,
            request_ip=request_ip,
            request_user_agent=request_user_agent,
            request_headers=json.dumps(request_headers) if request_headers else None,
            webhook_url=webhook_url,
            event_id=event_id,
            received_at=datetime.utcnow(),
            **kwargs
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    @staticmethod
    def get_log_by_id(log_id: str) -> Optional[WebhookLog]:
        """Get webhook log by ID."""
        return WebhookLog.query.get(log_id)
    
    @staticmethod
    def get_logs_by_account(
        account_id: str,
        limit: int = 100,
        offset: int = 0,
        status: str = None
    ) -> List[WebhookLog]:
        """Get webhook logs for an account."""
        query = WebhookLog.query.filter_by(instagram_account_id=account_id)
        
        if status:
            query = query.filter_by(processing_status=status)
        
        return query.order_by(WebhookLog.received_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_failed_logs(limit: int = 100) -> List[WebhookLog]:
        """Get failed webhook logs for retry."""
        return WebhookLog.query.filter(
            WebhookLog.processing_status == "failed",
            WebhookLog.retry_count < 4,
            db.or_(
                WebhookLog.next_retry_at.is_(None),
                WebhookLog.next_retry_at <= datetime.utcnow()
            )
        ).order_by(WebhookLog.received_at.asc()).limit(limit).all()
    
    @staticmethod
    def get_duplicate_by_event_id(event_id: str) -> Optional[WebhookLog]:
        """Check if webhook with same event_id exists."""
        if not event_id:
            return None
        return WebhookLog.query.filter_by(
            event_id=event_id,
            is_duplicate=False
        ).first()
    
    @staticmethod
    def update_log_status(
        log_id: str,
        status: str,
        error: str = None,
        signature_valid: bool = None,
        signature_error: str = None,
        parsed_payload: dict = None
    ) -> Optional[WebhookLog]:
        """Update webhook log status."""
        log = WebhookLogRepository.get_log_by_id(log_id)
        if not log:
            return None
        
        log.processing_status = status
        if error:
            log.processing_error = error
        if signature_valid is not None:
            log.signature_valid = signature_valid
        if signature_error:
            log.signature_validation_error = signature_error
        if parsed_payload:
            log.parsed_payload = json.dumps(parsed_payload)
        
        db.session.commit()
        return log
    
    @staticmethod
    def mark_as_processed(log_id: str, success: bool = True, error: str = None):
        """Mark webhook as processed."""
        log = WebhookLogRepository.get_log_by_id(log_id)
        if log:
            log.mark_processed(success=success, error=error)
            db.session.commit()
    
    @staticmethod
    def mark_as_duplicate(log_id: str, original_id: str):
        """Mark webhook as duplicate."""
        log = WebhookLogRepository.get_log_by_id(log_id)
        if log:
            log.mark_duplicate(original_id)
            db.session.commit()
    
    @staticmethod
    def get_stats_by_status(account_id: str = None) -> Dict[str, int]:
        """Get webhook log counts by status."""
        query = WebhookLog.query
        if account_id:
            query = query.filter_by(instagram_account_id=account_id)
        
        stats = {}
        for status in ['received', 'processing', 'processed', 'failed', 'duplicate']:
            count = query.filter_by(processing_status=status).count()
            stats[status] = count
        return stats
    
    @staticmethod
    def get_recent_logs(limit: int = 50) -> List[WebhookLog]:
        """Get recent webhook logs."""
        return WebhookLog.query.order_by(
            WebhookLog.received_at.desc()
        ).limit(limit).all()


class EventLogRepository:
    """Repository for event log database operations."""
    
    @staticmethod
    def create_log(
        instagram_account_id: str,
        event_type: str,
        event_time: datetime,
        webhook_log_id: str = None,
        event_id: str = None,
        sender_id: str = None,
        recipient_id: str = None,
        message_id: str = None,
        media_id: str = None,
        comment_id: str = None,
        event_data: dict = None,
        event_subtype: str = None,
        **kwargs
    ) -> EventLog:
        """Create a new event log entry."""
        log = EventLog(
            instagram_account_id=instagram_account_id,
            webhook_log_id=webhook_log_id,
            event_type=event_type,
            event_subtype=event_subtype,
            event_id=event_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_id=message_id,
            media_id=media_id,
            comment_id=comment_id,
            event_data=json.dumps(event_data) if event_data else None,
            event_time=event_time,
            processed_at=datetime.utcnow(),
            **kwargs
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    @staticmethod
    def get_log_by_id(log_id: str) -> Optional[EventLog]:
        """Get event log by ID."""
        return EventLog.query.get(log_id)
    
    @staticmethod
    def get_logs_by_account(
        account_id: str,
        limit: int = 100,
        offset: int = 0,
        event_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[EventLog]:
        """Get event logs for an account."""
        query = EventLog.query.filter_by(instagram_account_id=account_id)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        if start_date:
            query = query.filter(EventLog.event_time >= start_date)
        if end_date:
            query = query.filter(EventLog.event_time <= end_date)
        
        return query.order_by(EventLog.event_time.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def is_duplicate(event_id: str) -> bool:
        """Check if event has already been processed."""
        return EventLog.is_duplicate_event(event_id)
    
    @staticmethod
    def get_events_by_type(
        account_id: str,
        event_type: str,
        limit: int = 100
    ) -> List[EventLog]:
        """Get events by type for an account."""
        return EventLog.query.filter_by(
            instagram_account_id=account_id,
            event_type=event_type
        ).order_by(EventLog.event_time.desc()).limit(limit).all()
    
    @staticmethod
    def get_recent_events(limit: int = 50) -> List[EventLog]:
        """Get recent event logs."""
        return EventLog.query.order_by(
            EventLog.event_time.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_event_stats(
        account_id: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get event statistics."""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        query = EventLog.query.filter(EventLog.event_time >= start_date)
        
        if account_id:
            query = query.filter_by(instagram_account_id=account_id)
        
        total = query.count()
        
        # Count by event type
        type_counts = db.session.query(
            EventLog.event_type,
            db.func.count(EventLog.id)
        ).filter(
            EventLog.event_time >= start_date
        ).group_by(EventLog.event_type).all()
        
        return {
            "total_events": total,
            "by_type": {etype: count for etype, count in type_counts},
            "period_days": days
        }
    
    @staticmethod
    def update_status(log_id: str, status: str, error: str = None):
        """Update event log status."""
        log = EventLogRepository.get_log_by_id(log_id)
        if log:
            log.status = status
            if error:
                log.error_message = error
            db.session.commit()