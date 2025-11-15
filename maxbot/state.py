from typing import Any
from uuid import uuid8

class State:
    def __init__(self):
        self.uuid = uuid8()

class StateManager:
    states: dict[int, list[Any]] = {}
    _instance = None

    async def set_data(self, chat_id: int, name: str, value: Any):
        self.states[chat_id][1][name] = value

    async def get_data(self, chat_id: int, name: str):
        return self.states[chat_id][1][name]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def set_state(self, chat_id: int, state: State | Any):
        if chat_id in self.states.keys() and self.states[chat_id][1]:
            self.states[chat_id] = [state, self.states[chat_id][1]]
        else:
            self.states[chat_id] = [state, dict()]
    
    async def get_state(self, chat_id: int) -> State | Any:
        if chat_id in self.states.keys():
            return self.states[chat_id][0]
        else:
            return None
    
    async def erase_state(self, chat_id: int):
        if chat_id in self.states.keys():
            del self.states[chat_id]
    
    async def update(self, chat_id: int, name: str, data: Any):
        self.states[chat_id][1][name] = data
    
    async def get_all_data(self, chat_id: int) -> dict[str, Any]:
        return self.states[chat_id][1]
        