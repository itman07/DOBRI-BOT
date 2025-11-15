import asyncio
import time
from typing import Callable, Dict, List, Any, Optional

from maxbot.state import StateManager
from .bot import Bot
from ._types import Update, Message, CallbackQuery, Chat, User
from .filters import Filter
from .log import get_logger

logger = get_logger("dispatcher")

class Handler:
    def __init__(self, callback: Callable, filters: List[Filter] = None):
        self.callback = callback
        self.filters = filters or []
        self.name = callback.__name__

class Dispatcher:
    def __init__(self, bot: Bot):
        self._session = None
        self.stateManager = StateManager()
        self.bot = bot
        self.handlers: Dict[str, List[Handler]] = {
            "message": [],
            "callback_query": [],
            "my_chat_member": [],
            "bot_started": []
        }
        self._running = False
        self._processed_updates = 0
        self._start_time = None
        self._logger = get_logger("dispatcher")

    def bot_started_handler(self, *filters: Filter):
        def decorator(callback: Callable):
            handler = Handler(callback, list(filters))
            self.handlers["bot_started"].append(handler)
            self._logger.debug(f"Registered message handler: {handler.name}")
            return callback
        return decorator

    def message_handler(self, *filters: Filter):
        def decorator(callback: Callable):
            handler = Handler(callback, list(filters))
            self.handlers["message"].append(handler)
            self._logger.debug(f"Registered message handler: {handler.name}")
            return callback
        return decorator
    
    def callback_query_handler(self, *filters: Filter):
        def decorator(callback: Callable):
            handler = Handler(callback, list(filters))
            self.handlers["callback_query"].append(handler)
            self._logger.debug(f"Registered callback handler: {handler.name}")
            return callback
        return decorator
    
    async def process_update(self, update: Update):
        """Process single update"""
        self._processed_updates += 1
        update_type = None
        
        if update.message:
            update_type = "message"
            handlers = self.handlers["message"]
            user_id = update.effective_user.user_id if update.effective_user else "unknown"
            self._logger.debug(f"Processing message update {update.update_id} from user {user_id}")
        elif update.callback_query:
            update_type = "callback_query"
            handlers = self.handlers["callback_query"]
            user_id = update.effective_user.user_id if update.effective_user else "unknown"
            self._logger.debug(f"Processing callback update {update.update_id} from user {user_id}")
        elif update.update_type == "bot_started":
            update_type = "bot_started"
            handlers = self.handlers["bot_started"]
            user_id = update.effective_user.user_id if update.effective_user else "unknown"
            self._logger.debug(f"Processing callback update {update.update_id} from user {user_id}")
        else:
            self._logger.debug(f"Unknown update type: {update.update_type}")
            return
        
        handler_executed = False
        for handler in handlers:
            try:
                # Check filters
                passed = True
                for filter_obj in handler.filters:
                    if not await filter_obj(update):
                        passed = False
                        break
                
                if passed:
                    start_time = time.time()
                    self._logger.debug(f"Executing handler: {handler.name}")
                    
                    await handler.callback(update, self.bot, self.stateManager, self._session)
                    
                    execution_time = (time.time() - start_time) * 1000
                    self._logger.debug(f"Handler {handler.name} executed in {execution_time:.2f}ms")
                    
                    handler_executed = True
                    break  # Only first matching handler
                    
            except Exception as e:
                self._logger.error(f"Error in handler {handler.name}: {e}", exc_info=True)
        
        if not handler_executed:
            self._logger.debug(f"No handler found for update {update.update_id}")

    
    async def start_polling(self, timeout: int = 30, limit: int = 100, 
                           skip_updates: bool = False, reset_webhook: bool = True):
        """Start long polling"""
        self._running = True
        marker = None
        self._start_time = time.time()
        self._processed_updates = 0
        
        self._logger.info("Starting polling...")
        
        if skip_updates:
            self._logger.info("Skipping pending updates")
        
        if reset_webhook:
            self._logger.debug("Webhook reset is enabled")
        
        poll_attempts = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self._running:
            try:
                poll_attempts += 1
                self._logger.debug(f"Polling attempt #{poll_attempts}, timeout: {timeout}s")
                
                updates_data = await self.bot.get_updates(
                    timeout=timeout,
                    limit=limit,
                    marker=marker
                )
                
                consecutive_errors = 0  # Reset error counter on success
                
                if "updates" in updates_data:
                    updates = updates_data["updates"]
                    self._logger.info(f"Received {len(updates)} updates")
                    
                    for update_data in updates:
                        update = self._parse_update(update_data)
                        # print(update) #!!!
                        if update:
                            asyncio.create_task(self.process_update(update))
                    
                    # Update marker for next request
                    if "marker" in updates_data:
                        marker = updates_data["marker"]
                        self._logger.debug(f"Updated marker to: {marker}")
                else:
                    self._logger.debug("No updates in response")
                        
            except asyncio.CancelledError:
                self._logger.info("Polling cancelled")
                break
            except Exception as e:
                consecutive_errors += 1
                self._logger.error(f"Polling error (attempt {consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    self._logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping polling")
                    break
                
                await asyncio.sleep(5)
    
    def stop_polling(self):
        """Stop polling"""
        if self._running:
            self._running = False
            runtime = time.time() - self._start_time if self._start_time else 0
            self._logger.info(
                f"Polling stopped. Runtime: {runtime:.1f}s, "
                f"Processed updates: {self._processed_updates}"
            )
        else:
            self._logger.warning("Polling is not running")
    
    def _parse_update(self, update_data: Dict[str, Any]) -> Optional[Update]:
        """Parse update from API response"""
        try:
            update_type = update_data.get("update_type")
            
            message = None
            callback_query = None
            payload = None
            chat_id = None
            
            if update_type == "message_created":
                message_data = update_data.get("message", {})
                message = self._parse_message(message_data)
            elif update_type == "message_callback":
                callback_data = update_data.get("callback", {})
                message_data = update_data.get("message")
                callback_query = self._parse_callback_query(callback_data, message_data)
            elif update_type == "bot_started":
                payload = update_data.get("payload")
                chat_id = update_data.get("chat_id")

            
            return Update(
                update_id=update_data.get("timestamp", 0),
                update_type=update_type,
                timestamp=update_data.get("timestamp", 0),
                message=message,
                callback_query=callback_query,
                chat_id=chat_id,
                payload=payload
            )
        except Exception as e:
            self._logger.error(f"Error parsing update: {e}")
            return None
    
    def _parse_message(self, message_data: Dict[str, Any]) -> Optional[Message]:
        """Parse message from API response"""
        try:
            body = message_data.get("body", {})
            sender = message_data.get("sender", {})
            recipient = message_data.get("recipient", {})
            
            chat = Chat(
                chat_id=recipient.get("chat_id", 0),
                type=recipient.get("chat_type", "chat"),
                status="active",
                title=None
            )
            
            user = User(
                user_id=sender.get("user_id", 0),
                first_name=sender.get("first_name", ""),
                last_name=sender.get("last_name"),
                username=sender.get("username"),
                is_bot=sender.get("is_bot", False)
            )
            
            return Message(
                message_id=body.get("mid", ""),
                chat=chat,
                from_user=user,
                text=body.get("text"),
                timestamp=message_data.get("timestamp", 0),
                attachments=body.get("attachments")
            )
        except Exception as e:
            self._logger.error(f"Error parsing message: {e}")
            return None
    
    def _parse_callback_query(self, callback_data: Dict[str, Any], 
                            message_data: Optional[Dict[str, Any]]) -> Optional[CallbackQuery]:
        """Parse callback query from API response"""
        try:
            user_data = callback_data.get("user", {})
            message = self._parse_message(message_data) if message_data else None
            
            user = User(
                user_id=user_data.get("user_id", 0),
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name"),
                username=user_data.get("username"),
                is_bot=user_data.get("is_bot", False)
            )
            
            return CallbackQuery(
                callback_id=callback_data.get("callback_id", ""),
                from_user=user,
                message=message,
                payload=callback_data.get("payload"),
                timestamp=callback_data.get("timestamp", 0)
            )
        except Exception as e:
            self._logger.error(f"Error parsing callback query: {e}")
            return None