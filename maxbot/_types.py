from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class User:
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_bot: bool = False
    last_activity_time: Optional[int] = None

@dataclass
class Chat:
    chat_id: int
    type: str
    status: str
    title: Optional[str] = None
    participants_count: Optional[int] = None
    last_event_time: Optional[int] = None

@dataclass
class Message:
    message_id: str
    chat: Chat
    from_user: User
    text: Optional[str] = None
    timestamp: Optional[int] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    @property
    def chat_id(self) -> int:
        return self.chat.chat_id
    
    @property
    def from_id(self) -> int:
        return self.from_user.user_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text,
                "attachments": self.attachments,}

@dataclass
class CallbackQuery:
    callback_id: str
    from_user: User
    message: Optional[Message] = None
    payload: Optional[str] = None
    timestamp: Optional[int] = None

@dataclass
class Update:
    update_id: int
    update_type: str
    timestamp: int
    message: Optional[Message] = None
    callback_query: Optional[CallbackQuery] = None
    chat_id: Optional[int] = None
    payload: Optional[str] = None
    
    @property
    def effective_chat(self) -> Optional[Chat]:
        if self.message:
            return self.message.chat
        elif self.callback_query and self.callback_query.message:
            return self.callback_query.message.chat
        return None
    
    @property
    def effective_user(self) -> Optional[User]:
        if self.message:
            return self.message.from_user
        elif self.callback_query:
            return self.callback_query.from_user
        return None


# Keyboard types
@dataclass
class InlineKeyboardButton:
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        if self.callback_data:
            return {
                "type": "callback",
                "text": self.text,
                "payload": self.callback_data
            }
        elif self.url:
            return {
                "type": "link",
                "text": self.text,
                "url": self.url
            }
        return {"type": "callback", "text": self.text, "payload": self.text}


@dataclass
class InlineKeyboardMarkup:
    inline_keyboard: List[List[InlineKeyboardButton]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [button.to_dict() for button in row]
                    for row in self.inline_keyboard
                ]
            }
        }


# @dataclass
# class KeyboardButton:
#     text: str

#     def to_dict(self) -> Dict[str, Any]:
#         return {"text": self.text}


# @dataclass
# class ReplyKeyboardMarkup:
#     keyboard: List[List[KeyboardButton]]
#     resize_keyboard: bool = True

#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             "type": "reply_keyboard",
#             "payload": {
#                 "buttons": [
#                     [button.to_dict() for button in row]
#                     for row in self.keyboard
#                 ]
#             }
#         }