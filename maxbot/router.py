from typing import List
from .dispatcher import Dispatcher
from .filters import Filter
from .log import get_logger

logger = get_logger("router")

class Router:
    def __init__(self, name: str = "default"):
        self.name = name
        self.message_handlers: List = []
        self.callback_query_handlers: List = []
        self._logger = get_logger("router")
        self._logger.debug(f"Router '{name}' created")
    
    def message_handler(self, *filters: Filter):
        def decorator(callback):
            self.message_handlers.append((callback, list(filters)))
            self._logger.debug(f"Registered message handler in router '{self.name}': {callback.__name__}")
            return callback
        return decorator
    
    def callback_query_handler(self, *filters: Filter):
        def decorator(callback):
            self.callback_query_handlers.append((callback, list(filters)))
            self._logger.debug(f"Registered callback handler in router '{self.name}': {callback.__name__}")
            return callback
        return decorator
    
    def include_in_dispatcher(self, dispatcher: Dispatcher):
        """Include router handlers in dispatcher"""
        handler_count = 0
        
        for callback, filters in self.message_handlers:
            dispatcher.message_handler(*filters)(callback)
            handler_count += 1
        
        for callback, filters in self.callback_query_handlers:
            dispatcher.callback_query_handler(*filters)(callback)
            handler_count += 1
        
        self._logger.info(f"Included {handler_count} handlers from router '{self.name}' into dispatcher")