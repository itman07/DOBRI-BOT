from typing import Any, Optional
from ._types import Update
from .state import StateManager, State

class Filter:
    async def __call__(self, update: Update) -> bool:
        return True


class Command(Filter):
    def __init__(self, command: str):
        self.command = command.lower().lstrip('/')

    async def __call__(self, update: Update) -> bool:
        if not update.message or not update.message.text:
            return False

        text = update.message.text.lower()
        if text.startswith('/'):
            command = text[1:].split(' ')[0].split('@')[0]
            return command == self.command
        return False


class Text(Filter):
    def __init__(self, text: str):
        self.text = text.lower()

    async def __call__(self, update: Update) -> bool:
        if not update.message or not update.message.text:
            return False
        return update.message.text.lower() == self.text


class StateFilter(Filter):
    def __init__(self, state: Any):
        self._stateManager = StateManager()
        self.state = state

    async def __call__(self, update: Update) -> bool:
        saved_state = await self._stateManager.get_state(update.effective_chat.chat_id)
        if type(self.state) is State and type(saved_state) is State:
            
            return self.state.uuid == saved_state.uuid 
        else:
            return isinstance(await self._stateManager.get_state(update.effective_chat.chat_id), type(self.state))
        


class CallbackQueryFilter(Filter):
    def __init__(self, data: Optional[str] = None):
        self.data = data

    async def __call__(self, update: Update) -> bool:
        if not update.callback_query:
            return False
        if self.data and update.callback_query.payload != self.data:
            return False
        return True

# class BotStarted(Filter):
#     def __init__(self):
#         super().__init__()
#     async def __call__(self, update: Update) -> bool:
#         return update.update_type == 'bot_started'
