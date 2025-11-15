import asyncio
import logging
from maxbot import Bot, Dispatcher, StateFilter, Command, State, InlineKeyboardMarkup, InlineKeyboardButton
from maxbot._types import Update
from maxbot.log import configure_logging
from maxbot.state import StateManager

# Configure logging
configure_logging(level=logging.INFO)


class Form:
    name = State()
    age = State()
    confirm = State()

# Create bot and dispatcher
bot = Bot("f9LHodD0cOIPRyzuSVEQMG9_pjAcwioS7IRzEqf_LJi82cOb4D88uusFdBkEPa_VUZhp-MP3O3vUCLoNRGHc")
dp = Dispatcher(bot)

@dp.message_handler(Command("start"))
async def start_command(update: Update, bot: Bot, stateManager: StateManager):
    await stateManager.set_state(update.effective_chat.chat_id, Form.name)
    await bot.send_message(
        update.effective_chat.chat_id,
        "Welcome! Please enter your name:"
    )

@dp.message_handler(StateFilter(Form.name))
async def process_name(update: Update, bot: Bot, stateManager: StateManager):
    await stateManager.update(update.effective_chat.chat_id, "name", update.message.text)
    await stateManager.set_state(update.effective_chat.chat_id, Form.age)
    await bot.send_message(
        update.effective_chat.chat_id,
        f"Nice to meet you, {update.message.text}! Now please enter your age:"
    )

@dp.message_handler(StateFilter(Form.age))
async def process_age(update: Update, bot: Bot, stateManager: StateManager):
    try:
        age = int(update.message.text)
        await stateManager.update(update.effective_chat.chat_id, "age", age)
        
        data = await stateManager.get_all_data(update.effective_chat.chat_id)
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Yes", callback_data="confirm_yes"),
                InlineKeyboardButton("No", callback_data="confirm_no")
            ]
        ])
        
        await stateManager.set_state(update.effective_chat.chat_id, Form.confirm)
        await bot.send_message(
            update.effective_chat.chat_id,
            f"Please confirm your details:\n"
            f"Name: {data['name']}\n"
            f"Age: {data['age']}",
            attachments=[keyboard.to_dict()]
        )
    except ValueError:
        await bot.send_message(
            update.effective_chat.chat_id,
            "Please enter a valid number for age."
        )

async def check_payload_yes(update):
    return update.callback_query.payload == "confirm_yes"

@dp.callback_query_handler(check_payload_yes)
async def confirm_yes(update: Update, bot: Bot, stateManager: StateManager):
    data = await stateManager.get_all_data(update.effective_chat.chat_id)
    await bot.send_message(
        update.effective_chat.chat_id,
        f"Thank you for registration, {data['name']}! Your data has been saved."
    )
    await stateManager.erase_state(update.effective_chat.chat_id,)

async def check_payload_no(update):
    return update.callback_query.payload == "confirm_no"

@dp.callback_query_handler(check_payload_no)
async def confirm_no(update: Update, bot: Bot, stateManager: StateManager):
    await stateManager.set_state(update.effective_chat.chat_id, Form.name)
    await bot.send_message(
        update.effective_chat.chat_id,
        "Let's start over. Please enter your name:"
    )
    await bot.answer_callback(update.callback_query.callback_id, "Registration cancelled")

@dp.message_handler(Command("cancel"))
async def cancel_command(update: Update, bot: Bot, stateManager: StateManager):
    current_state = await stateManager.get_state(update.effective_chat.chat_id)
    if current_state:
        await stateManager.erase(update.effective_chat.chat_id)
        await bot.send_message(
            update.effective_chat.chat_id,
            "Current operation cancelled."
        )
    else:
        await bot.send_message(
            update.effective_chat.chat_id,
            "No active operation to cancel."
        )

async def main():
    async with bot:
        await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
