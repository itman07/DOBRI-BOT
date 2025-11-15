import aiohttp
from typing import Optional, Dict, Any
from .log import get_logger

logger = get_logger("bot")

class Bot:
    def __init__(self, token: str, base_url: str = "https://platform-api.max.ru"):
        self.token = token
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._logger = get_logger("bot")
        
    async def __aenter__(self):
        await self.setup()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def setup(self):
        """Initialize aiohttp session"""
        self._logger.debug("Setting up aiohttp session")
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            headers={"Content-Type": "application/json"}
        )
        self._logger.info("Bot session initialized")
        
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            self._logger.debug("Closing aiohttp session")
            await self.session.close()
            self._logger.info("Bot session closed")
            
    def _build_url(self, method: str) -> str:
        """Build URL with access token"""
        return f"{method}?access_token={self.token}"
    
    async def get_me(self) -> Dict[str, Any]:
        """Get bot info"""
        self._logger.debug("Getting bot info")
        async with self.session.get(self._build_url("/me")) as response:
            data = await response.json()
            self._logger.debug(f"Bot info received: {data}")
            return data
    
    async def get_updates(self, limit: int = 100, timeout: int = 30, 
                         marker: Optional[int] = None, types: Optional[list] = None) -> Dict[str, Any]:
        """Get updates via long polling"""
        params = {"limit": limit, "timeout": timeout}
        if marker:
            params["marker"] = marker
        if types:
            params["types"] = ",".join(types)
            
        self._logger.debug(f"Getting updates with params: {params}")
        
        async with self.session.get(self._build_url("/updates"), params=params) as response:
            data = await response.json()
            updates_count = len(data.get("updates", []))
            self._logger.debug(f"Received {updates_count} updates")
            return data
    
    async def send_message(self,
                           chat_id: int | None = None,
                           user_id: int | None = None,
                           text: str | None = "",
                           attachments: Optional[list] = None,
                           format: Optional[str] = None,
                           disable_link_preview: bool = False) -> Dict[str, Any]:
        """Send message to chat"""
        payload = {
            "text": text,
            "attachments": attachments or [],
            "notify": True
        }
        params = {}

        if not (chat_id or user_id):
            raise ValueError("Couldn't send message: user id or chat id is not specified.")
        elif chat_id:
            params["chat_id"] = chat_id
        elif user_id:
            params["user_id"] = user_id

        if format:
            payload["format"] = format
        if disable_link_preview:
            payload["disable_link_preview"] = disable_link_preview
            
        
        
        self._logger.debug(f"Sending message to chat {chat_id}: {text[:50]}...")
        
        async with self.session.post(
            self._build_url("/messages"), 
            params=params,
            json=payload
        ) as response:
            data = await response.json()
            message_id = data.get("message", {}).get("body", {}).get("mid", "unknown")
            self._logger.info(f"Message sent to chat {chat_id}, message_id: {message_id}")
            return data
    
    async def answer_callback(
        self,
        callback_id: str,
        text: Optional[str] = None, 
        attachments: Optional[list] = None,
        format: Optional[str] = None,
        notification: Optional[str] = None
    ) -> Dict[str, Any]:
        """Answer callback query and edit last message."""
        payload = {}

        if text or attachments:

            payload["message"] = {}
            
            if text:
                payload["message"]["text"] = text
            if attachments:
                payload["message"]["attachments"] = attachments
            if format:
                payload["message"]["format"] = format

        if notification:
            payload["notification"] = notification
            
        params = {"callback_id": callback_id}
        
        self._logger.debug(f"Answering callback {callback_id}")
        
        async with self.session.post(
            self._build_url("/answers"),
            params=params,
            json=payload
        ) as response:
            data = await response.json()
            self._logger.debug(f"Callback {callback_id} answered")
            return data
    
    async def edit_message(self, message_id: str, text: str,
                          attachments: Optional[list] = None) -> Dict[str, Any]:
        """Edit message"""
        payload = {
            "text": text,
            "attachments": attachments or []
        }
        
        params = {"message_id": message_id}
        
        self._logger.debug(f"Editing message {message_id}")
        
        async with self.session.put(
            self._build_url("/messages"),
            params=params,
            json=payload
        ) as response:
            data = await response.json()
            self._logger.info(f"Message {message_id} edited")
            return data
    
    async def delete_message(self, message_id: str) -> Dict[str, Any]:
        """Delete message"""
        params = {"message_id": message_id}
        
        self._logger.debug(f"Deleting message {message_id}")
        
        async with self.session.delete(
            self._build_url("/messages"),
            params=params
        ) as response:
            data = await response.json()
            self._logger.info(f"Message {message_id} deleted")
            return data
    
    async def get_chat(self, chat_id: int) -> Dict[str, Any]:
        """Get chat info"""
        self._logger.debug(f"Getting chat info for {chat_id}")
        
        async with self.session.get(
            self._build_url(f"/chats/{chat_id}")
        ) as response:
            data = await response.json()
            self._logger.debug(f"Chat info received for {chat_id}")
            return data

    async def health_check(self) -> bool:
        """Perform health check by getting bot info"""
        try:
            await self.get_me()
            self._logger.debug("Health check passed")
            return True
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return False