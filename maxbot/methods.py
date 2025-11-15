# from ._types import InlineKeyboardMarkup

# class MessageMethods:
#     def __init__(self, bot):
#         self.bot = bot

#     async def answer(self, chat_id: int, text: str,
#                      reply_markup: InlineKeyboardMarkup = None,
#                      **kwargs) -> dict:
#         """Send message with optional keyboard"""
#         attachments = []
#         if reply_markup:
#             attachments.append(reply_markup.to_dict())

#         return await self.bot.send_message(
#             chat_id=chat_id,
#             text=text,
#             attachments=attachments,
#             **kwargs
#         )

#     async def edit_text(self, message_id: str, text: str,
#                         reply_markup: InlineKeyboardMarkup = None) -> dict:
#         """Edit message text and keyboard"""
#         attachments = []
#         if reply_markup:
#             attachments.append(reply_markup.to_dict())

#         return await self.bot.edit_message(
#             message_id=message_id,
#             text=text,
#             attachments=attachments
#         )


# class CallbackQueryMethods:
#     def __init__(self, bot):
#         self.bot = bot

#     async def answer(self, callback_id: str,
#                      text: str = None,
#                      show_alert: bool = False) -> dict:
#         """Answer callback query"""
#         notification = text if show_alert else None
#         return await self.bot.answer_callback(
#             callback_id=callback_id,
#             notification=notification
#         )