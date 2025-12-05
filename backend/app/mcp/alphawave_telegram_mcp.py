"""
Telegram MCP Integration for Nicole V7

Provides Telegram bot messaging capabilities.
Uses direct Telegram Bot API as a fallback when MCP is unavailable.

Features:
- Send text messages
- Send documents/files
- Send photos
- Send with formatting (Markdown/HTML)
"""

from typing import Any, Dict, Optional
import logging
import httpx
import os

from app.mcp.alphawave_mcp_manager import mcp_manager, AlphawaveMCPManager, FallbackMCPManager
from app.config import settings

logger = logging.getLogger(__name__)


class AlphawaveTelegramMCP:
    """
    Telegram MCP integration.
    
    Provides Telegram bot messaging functionality.
    Falls back to direct HTTP API calls if MCP unavailable.
    """
    
    SERVER_NAME = "telegram"
    
    def __init__(self):
        """Initialize Telegram MCP."""
        self._connected = False
        self._bot_token = settings.TELEGRAM_BOT_TOKEN
        self._default_chat_id = settings.GLEN_TELEGRAM_CHAT_ID
    
    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self._bot_token)
    
    @property
    def is_connected(self) -> bool:
        """Check if Telegram MCP server is connected."""
        # Telegram can work via direct API, so check if configured
        return self.is_configured
    
    async def connect(self) -> bool:
        """
        Connect to Telegram service.
        
        For Telegram, we use direct API calls as it's more reliable
        than running an MCP server subprocess.
        
        Returns:
            True if configuration is valid
        """
        if not self._bot_token:
            logger.warning("[Telegram] Bot token not configured")
            return False
        
        # Test the bot token
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{self._bot_token}/getMe"
                )
                if response.status_code == 200:
                    data = response.json()
                    bot_name = data.get("result", {}).get("username", "unknown")
                    logger.info(f"[Telegram] Connected as @{bot_name}")
                    self._connected = True
                    return True
                else:
                    logger.error(f"[Telegram] Invalid bot token: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"[Telegram] Connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram service."""
        self._connected = False
    
    # =========================================================================
    # MESSAGING
    # =========================================================================
    
    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = "Markdown",
        disable_notification: bool = False
    ) -> Dict[str, Any]:
        """
        Send a text message via Telegram.
        
        Args:
            text: Message text
            chat_id: Telegram chat ID (defaults to Glen's chat)
            parse_mode: 'Markdown', 'HTML', or None
            disable_notification: Send silently
            
        Returns:
            Send result with message ID
        """
        if not self.is_configured:
            return {"error": "Telegram bot token not configured"}
        
        target_chat = chat_id or self._default_chat_id
        if not target_chat:
            return {"error": "No chat_id provided and no default configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "chat_id": target_chat,
                    "text": text,
                    "disable_notification": disable_notification
                }
                
                if parse_mode:
                    payload["parse_mode"] = parse_mode
                
                response = await client.post(
                    f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("result", {}).get("message_id")
                    logger.info(f"[Telegram] Sent message {message_id} to {target_chat}")
                    return {
                        "status": "sent",
                        "message_id": message_id,
                        "chat_id": target_chat
                    }
                else:
                    error_msg = response.json().get("description", response.text)
                    logger.error(f"[Telegram] Send failed: {error_msg}")
                    return {"error": error_msg}
                    
        except Exception as e:
            logger.error(f"[Telegram] Send error: {e}")
            return {"error": str(e)}
    
    async def send_document(
        self,
        document_url: str,
        chat_id: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a document/file via Telegram.
        
        Args:
            document_url: URL of the document to send
            chat_id: Target chat ID
            caption: Optional caption text
            
        Returns:
            Send result
        """
        if not self.is_configured:
            return {"error": "Telegram bot token not configured"}
        
        target_chat = chat_id or self._default_chat_id
        if not target_chat:
            return {"error": "No chat_id provided"}
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "chat_id": target_chat,
                    "document": document_url
                }
                
                if caption:
                    payload["caption"] = caption
                
                response = await client.post(
                    f"https://api.telegram.org/bot{self._bot_token}/sendDocument",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"[Telegram] Sent document to {target_chat}")
                    return {"status": "sent", "chat_id": target_chat}
                else:
                    return {"error": response.json().get("description", response.text)}
                    
        except Exception as e:
            logger.error(f"[Telegram] Document send error: {e}")
            return {"error": str(e)}
    
    async def send_photo(
        self,
        photo_url: str,
        chat_id: Optional[str] = None,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a photo via Telegram.
        
        Args:
            photo_url: URL of the photo to send
            chat_id: Target chat ID
            caption: Optional caption text
            
        Returns:
            Send result
        """
        if not self.is_configured:
            return {"error": "Telegram bot token not configured"}
        
        target_chat = chat_id or self._default_chat_id
        if not target_chat:
            return {"error": "No chat_id provided"}
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "chat_id": target_chat,
                    "photo": photo_url
                }
                
                if caption:
                    payload["caption"] = caption
                
                response = await client.post(
                    f"https://api.telegram.org/bot{self._bot_token}/sendPhoto",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"[Telegram] Sent photo to {target_chat}")
                    return {"status": "sent", "chat_id": target_chat}
                else:
                    return {"error": response.json().get("description", response.text)}
                    
        except Exception as e:
            logger.error(f"[Telegram] Photo send error: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================
    
    async def notify_glen(self, message: str) -> Dict[str, Any]:
        """
        Send a notification to Glen's Telegram.
        
        Args:
            message: Notification text
            
        Returns:
            Send result
        """
        if not self._default_chat_id:
            return {"error": "Glen's chat ID not configured"}
        
        return await self.send_message(message, chat_id=self._default_chat_id)
    
    async def send_daily_summary(self, summary: str) -> Dict[str, Any]:
        """
        Send a daily summary message.
        
        Args:
            summary: Summary text (markdown supported)
            
        Returns:
            Send result
        """
        formatted = f"📋 *Daily Summary*\n\n{summary}"
        return await self.notify_glen(formatted)
    
    async def send_alert(self, title: str, message: str) -> Dict[str, Any]:
        """
        Send an alert notification.
        
        Args:
            title: Alert title
            message: Alert details
            
        Returns:
            Send result
        """
        formatted = f"⚠️ *{title}*\n\n{message}"
        return await self.notify_glen(formatted)
    
    async def send_sports_update(self, update: str) -> Dict[str, Any]:
        """
        Send a sports oracle update.
        
        Args:
            update: Sports update text
            
        Returns:
            Send result
        """
        formatted = f"🏈 *Sports Oracle*\n\n{update}"
        return await self.notify_glen(formatted)


# Global instance
telegram_mcp = AlphawaveTelegramMCP()
