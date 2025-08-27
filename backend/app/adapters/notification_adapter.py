"""Notification adapters for webhooks and other notification systems."""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from urllib.parse import urljoin

from ..domain.bom import OnshapeReference
from ..application.services import NotificationPort


logger = logging.getLogger(__name__)


class WebhookNotificationAdapter:
    """Webhook-based notification adapter."""
    
    def __init__(
        self,
        webhook_urls: List[str],
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.webhook_urls = webhook_urls
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def notify_bom_updated(self, onshape_ref: OnshapeReference) -> None:
        """Notify that BOM was updated."""
        
        payload = {
            "event": "bom_updated",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "document_id": onshape_ref.document_id,
                "element_id": onshape_ref.element_id,
                "wvm_type": onshape_ref.wvm_type,
                "wvm_id": onshape_ref.wvm_id
            }
        }
        
        await self._send_webhook(payload)
    
    async def notify_thumbnails_ready(self, onshape_ref: OnshapeReference) -> None:
        """Notify that thumbnails are ready."""
        
        payload = {
            "event": "thumbnails_ready",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "document_id": onshape_ref.document_id,
                "element_id": onshape_ref.element_id,
                "wvm_type": onshape_ref.wvm_type,
                "wvm_id": onshape_ref.wvm_id
            }
        }
        
        await self._send_webhook(payload)
    
    async def notify_fab_pack_ready(
        self,
        onshape_ref: OnshapeReference,
        package_id: str,
        file_count: int
    ) -> None:
        """Notify that fabrication package is ready."""
        
        payload = {
            "event": "fab_pack_ready",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "document_id": onshape_ref.document_id,
                "element_id": onshape_ref.element_id,
                "wvm_type": onshape_ref.wvm_type,
                "wvm_id": onshape_ref.wvm_id,
                "package_id": package_id,
                "file_count": file_count
            }
        }
        
        await self._send_webhook(payload)
    
    async def notify_processing_error(
        self,
        onshape_ref: OnshapeReference,
        operation: str,
        error_message: str
    ) -> None:
        """Notify about processing errors."""
        
        payload = {
            "event": "processing_error",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "document_id": onshape_ref.document_id,
                "element_id": onshape_ref.element_id,
                "wvm_type": onshape_ref.wvm_type,
                "wvm_id": onshape_ref.wvm_id,
                "operation": operation,
                "error": error_message
            }
        }
        
        await self._send_webhook(payload)
    
    async def _send_webhook(self, payload: Dict[str, Any]) -> None:
        """Send webhook to all configured URLs."""
        
        if not self.webhook_urls:
            logger.debug("No webhook URLs configured, skipping notification")
            return
        
        # Send to all webhooks concurrently
        tasks = [
            self._send_single_webhook(url, payload)
            for url in self.webhook_urls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Webhook {self.webhook_urls[i]} failed: {result}")
    
    async def _send_single_webhook(self, url: str, payload: Dict[str, Any]) -> None:
        """Send webhook to a single URL with retries."""
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DesignAssistant/1.0"
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.debug(f"Webhook sent successfully to {url}")
                    return
                else:
                    logger.warning(f"Webhook {url} returned {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Webhook {url} attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        logger.error(f"Webhook {url} failed after {self.max_retries + 1} attempts")


class SlackNotificationAdapter:
    """Slack-specific notification adapter."""
    
    def __init__(self, webhook_url: str, channel: str = "#general"):
        self.webhook_url = webhook_url
        self.channel = channel
        self.client = httpx.AsyncClient()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def notify_bom_updated(self, onshape_ref: OnshapeReference) -> None:
        """Send Slack notification for BOM update."""
        
        message = {
            "channel": self.channel,
            "username": "Design Assistant",
            "icon_emoji": ":gear:",
            "text": f"BOM updated for document {onshape_ref.document_id[:8]}...",
            "attachments": [
                {
                    "color": "good",
                    "fields": [
                        {
                            "title": "Document ID",
                            "value": onshape_ref.document_id,
                            "short": True
                        },
                        {
                            "title": "Element ID", 
                            "value": onshape_ref.element_id,
                            "short": True
                        },
                        {
                            "title": "Updated",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        await self._send_slack_message(message)
    
    async def notify_thumbnails_ready(self, onshape_ref: OnshapeReference) -> None:
        """Send Slack notification for thumbnails."""
        
        message = {
            "channel": self.channel,
            "username": "Design Assistant",
            "icon_emoji": ":camera:",
            "text": f"Thumbnails generated for document {onshape_ref.document_id[:8]}..."
        }
        
        await self._send_slack_message(message)
    
    async def notify_processing_error(
        self,
        onshape_ref: OnshapeReference,
        operation: str,
        error_message: str
    ) -> None:
        """Send Slack notification for errors."""
        
        message = {
            "channel": self.channel,
            "username": "Design Assistant",
            "icon_emoji": ":warning:",
            "text": f"Error in {operation} for document {onshape_ref.document_id[:8]}...",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {
                            "title": "Operation",
                            "value": operation,
                            "short": True
                        },
                        {
                            "title": "Error",
                            "value": error_message,
                            "short": False
                        }
                    ]
                }
            ]
        }
        
        await self._send_slack_message(message)
    
    async def _send_slack_message(self, message: Dict[str, Any]) -> None:
        """Send message to Slack."""
        
        try:
            response = await self.client.post(self.webhook_url, json=message)
            
            if response.status_code != 200:
                logger.error(f"Slack notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")


class EmailNotificationAdapter:
    """Email notification adapter (placeholder implementation)."""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int = 587,
        username: str = "",
        password: str = "",
        from_email: str = "",
        to_emails: List[str] = None
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails or []
    
    async def notify_bom_updated(self, onshape_ref: OnshapeReference) -> None:
        """Send email notification for BOM update."""
        
        subject = f"BOM Updated - {onshape_ref.document_id[:8]}"
        body = f"""
        BOM has been updated for document {onshape_ref.document_id}.
        
        Details:
        - Document ID: {onshape_ref.document_id}
        - Element ID: {onshape_ref.element_id}
        - Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self._send_email(subject, body)
    
    async def notify_thumbnails_ready(self, onshape_ref: OnshapeReference) -> None:
        """Send email notification for thumbnails."""
        
        subject = f"Thumbnails Ready - {onshape_ref.document_id[:8]}"
        body = f"""
        Thumbnails have been generated for document {onshape_ref.document_id}.
        
        Document ID: {onshape_ref.document_id}
        Element ID: {onshape_ref.element_id}
        """
        
        await self._send_email(subject, body)
    
    async def _send_email(self, subject: str, body: str) -> None:
        """Send email (placeholder implementation)."""
        # This would use aiosmtplib or similar for actual email sending
        logger.info(f"Email notification: {subject}")
        logger.debug(f"Email body: {body}")


class CompositeNotificationAdapter:
    """Composite notification adapter that sends to multiple channels."""
    
    def __init__(self, adapters: List[NotificationPort]):
        self.adapters = adapters
    
    async def notify_bom_updated(self, onshape_ref: OnshapeReference) -> None:
        """Send notification to all adapters."""
        await self._notify_all("notify_bom_updated", onshape_ref)
    
    async def notify_thumbnails_ready(self, onshape_ref: OnshapeReference) -> None:
        """Send notification to all adapters."""
        await self._notify_all("notify_thumbnails_ready", onshape_ref)
    
    async def _notify_all(self, method_name: str, *args, **kwargs) -> None:
        """Send notification to all adapters concurrently."""
        
        tasks = []
        for adapter in self.adapters:
            method = getattr(adapter, method_name, None)
            if method:
                tasks.append(method(*args, **kwargs))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    adapter_name = self.adapters[i].__class__.__name__
                    logger.error(f"Notification adapter {adapter_name} failed: {result}")


class NullNotificationAdapter:
    """Null notification adapter that does nothing (for testing)."""
    
    async def notify_bom_updated(self, onshape_ref: OnshapeReference) -> None:
        """No-op notification."""
        pass
    
    async def notify_thumbnails_ready(self, onshape_ref: OnshapeReference) -> None:
        """No-op notification."""
        pass