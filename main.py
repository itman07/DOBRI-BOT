import asyncio
from dataclasses import dataclass
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from create_db import update_pet, delete_photo_by_token, delete_pet_by_id, get_shelters_without_verification, \
    delete_shelter_by_max_id

from create_db import create_db, get_pet_by_id, get_pets_by_location, get_photos_by_pet_id, get_shelter_by_max_id, \
    create_shelter, create_pet, create_photo, update_shelter, \
    get_shelter_by_id, get_shelters_by_location, get_user_by_max_id, create_user, get_pets_by_shelter_id, update_user
from maxbot import Bot, Dispatcher, Update, StateManager, State, configure_logging, StateFilter
from maxbot._types import InlineKeyboardButton, InlineKeyboardMarkup
from maxbot.filters import Command
from models import Pet, Shelter, User
from string_token import token_str

configure_logging(level=logging.DEBUG)

bot = Bot(token_str)
dp = Dispatcher(bot)
city = State()
volunteer_city = State()
shelters = State()
search = State()
warn = State()

moderators: list[int] = []


@dataclass
class ShelterRegistration:
    name = State()
    address = State()
    url = State()
    description = State()
    get_messages = State()
    location = State()


@dataclass
class ShelterChange:
    name = State()
    address = State()
    url = State()
    description = State()
    get_messages = State()


@dataclass
class AnimalRegistration:
    _type = State()
    name = State()
    age = State()
    gender = State()
    description = State()
    media = State()


@dataclass
class AnimalChange:
    _type = State()
    name = State()
    age = State()
    gender = State()
    description = State()
    media = State()


@dp.message_handler(Command("start"))
@dp.bot_started_handler()
async def start(update: Update, bot: Bot, stateManager: StateManager, session):
    update.chat_id = update.chat_id if update.chat_id else update.message.chat_id
    await bot.send_message(chat_id=update.chat_id, text=
    "Вас приветствует ДОБРИ БОТ! Я умею:\n\n" \
    "- Помогать в поиске питомца из приюта.\n" \
    "- Связывать волонтёров с приютами.")

    await bot.send_message(chat_id=update.chat_id,
                           text="Для чего вы здесь?",
                           attachments=[
                               InlineKeyboardMarkup([[InlineKeyboardButton("Хочу завести животное", "get_animal")],
                                                     [InlineKeyboardButton("Хочу помочь приютам", "volunteer")],
                                                     [InlineKeyboardButton("Администрация приюта",
                                                                           "new_shelter")]]).to_dict()])


async def new_user_callback(update: Update):
    return update.callback_query.payload == "get_animal"


async def shelter_search_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "shelter_search"


async def volunteer_callback(update: Update):
    return update.callback_query.payload == "volunteer"


async def new_shelter_callback(update: Update):
    return update.callback_query.payload == "new_shelter"


@dp.callback_query_handler(volunteer_callback)
async def volunteer_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await bot.send_message(chat_id=update.callback_query.message.chat_id, text="Назовите город, в котором вы сейчас.")
    await stateManager.set_state(update.callback_query.message.chat_id, volunteer_city)


@dp.message_handler(StateFilter(volunteer_city))
async def volunteer_search_hanlder(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.erase_state(update.message.chat_id)
    await stateManager.set_state(update.message.chat_id, shelters)
    await stateManager.set_data(update.message.chat_id, "city", update.message.text)
    await bot.send_message(chat_id=update.message.chat_id,
                              text="Теперь я могу приступить к поиску приюта! Начнём?",
                              attachments=[InlineKeyboardMarkup(
                                  [[InlineKeyboardButton("Поехали!", "shelter_search:_")]]).to_dict()])


@dp.callback_query_handler(shelter_search_callback)
async def shelter_search_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    if update.callback_query.payload.split(":")[1] == "_":

        location: str = await stateManager.get_data(update.callback_query.message.chat_id, "city")
        shelters: list[Shelter] = await get_shelters_by_location(session, location.lower())

        await stateManager.set_data(update.callback_query.message.chat_id, "shelters",
                                    [s for s in shelters if s.verified == 1 and (s.dobro_rf or s.get_messages)])
        await stateManager.set_data(update.callback_query.message.chat_id, "shelters_index", 0)
    elif update.callback_query.payload.split(":")[1] == "like":
        shelter: Shelter = await get_shelter_by_id(session, int(update.callback_query.payload.split(":")[2]))
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text=f"Свяжитесь с приютом {f"через его страницу на dobro.ru: {shelter.dobro_rf}" if shelter.dobro_rf else f"через его профиль в MAX: https://max.ru/{shelter.max_id}"}")

    shelter_index: int = await stateManager.get_data(update.callback_query.message.chat_id, "shelters_index")
    shelters: list[Shelter] = await stateManager.get_data(update.callback_query.message.chat_id, "shelters")

    if shelter_index < len(shelters):
        shelter: Shelter = shelters[shelter_index]
    else:
        await bot.answer_callback(
            update.callback_query.callback_id,
            "Больше нет подтверждённых приютов в этом городе.")
        await stateManager.erase_state(update.callback_query.message.chat_id)
        return

    # anketa: dict[str, str] = {
    #     "id": 1234,
    #     "name": "Сокольнический",
    #     "address": "Москва, метро Сокольники, ...",
    #     "description": "VIP Приют города",
    #     "get_messages": 1,
    #     "url": "https://dobro.ru"
    # }

    await bot.answer_callback(
        update.callback_query.callback_id,
        f"Приют {shelter.name}, {shelter.address}\n" \
        f"{shelter.description}",
        [InlineKeyboardMarkup([[InlineKeyboardButton("Откликнуться", f"shelter_search:like:{shelter.id}"),
                                InlineKeyboardButton("Дальше", f"shelter_search:next:{shelter.id}")]]).to_dict()])
    await stateManager.set_data(update.callback_query.message.chat_id, "shelters_index", shelter_index + 1)


@dp.callback_query_handler(new_shelter_callback)
async def new_shelter_handler(update: Update, bot: Bot, stateManager: StateManager, session: AsyncSession):
    is_exist: bool = await get_shelter_by_max_id(session, update.callback_query.from_user.user_id) is not None
    if is_exist:
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Вы уже зарегистрированы в качестве приюта.")
    else:
        await bot.answer_callback(update.callback_query.callback_id, notification="Регистрирую ваш приют.")
        await bot.send_message(chat_id=update.callback_query.message.chat_id, text="Отправьте название приюта.")
        await stateManager.set_state(update.callback_query.message.chat_id, ShelterRegistration.name)


@dp.message_handler(StateFilter(ShelterRegistration.name))
async def shelter_city_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.message.chat_id, "name", update.message.text)
    await bot.send_message(chat_id=update.message.chat_id, text="Отправьте город приюта.")
    await stateManager.set_state(update.message.chat_id, ShelterRegistration.location)


@dp.message_handler(StateFilter(ShelterRegistration.location))
async def shelter_name_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.message.chat_id, "location", update.message.text)
    await bot.send_message(chat_id=update.message.chat_id, text="Отправьте адрес приюта.")
    await stateManager.set_state(update.message.chat_id, ShelterRegistration.address)


@dp.message_handler(StateFilter(ShelterRegistration.address))
async def shelter_address_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.message.chat_id, "address", update.message.text)
    await bot.send_message(chat_id=update.message.chat_id,
                           text="Отправьте ссылку на вашу страницу или страницу вашего события на dobro.ru",
                           attachments=[
                               InlineKeyboardMarkup([[InlineKeyboardButton("Нет страницы", "skip_url")]]).to_dict()])
    await stateManager.set_state(update.message.chat_id, ShelterRegistration.url)


async def skip_url_callback(update: Update):
    return update.callback_query.payload == "skip_url"


@dp.callback_query_handler(skip_url_callback)
async def shelter_skip_url_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await bot.answer_callback(update.callback_query.callback_id, notification="Ссылка пропущена.")
    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Отправьте описание приюта.",
                           attachments=[InlineKeyboardMarkup(
                               [[InlineKeyboardButton("Без описания", "skip_description")]]).to_dict()])
    await stateManager.set_state(update.callback_query.message.chat_id, ShelterRegistration.description)


@dp.message_handler(StateFilter(ShelterRegistration.url))
async def shelter_url_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    if "dobro.ru" in update.message.text:
        await stateManager.set_data(update.message.chat_id, "url", update.message.text)
    else:
        return await bot.send_message(chat_id=update.message.chat_id,
                                      text="Вы ввели неверную ссылку. Пожалуйста, введите верную или пропустите этот шаг.")
    await bot.send_message(chat_id=update.message.chat_id,
                           text="Отправьте описание приюта.",
                           attachments=[InlineKeyboardMarkup(
                               [[InlineKeyboardButton("Без описания", "skip_description")]]).to_dict()])
    await stateManager.set_state(update.message.chat_id, ShelterRegistration.description)


async def skip_description_callback(update: Update):
    return update.callback_query.payload == "skip_description"


@dp.callback_query_handler(skip_description_callback)
async def shelter_skip_description_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await bot.answer_callback(update.callback_query.callback_id, notification="Описание пропущено.")
    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Давать ли ссылку на ваш аккаунт в MAX человеку, который захочет забрать животное?",
                           attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Нет", "get_messages:no"),
                                                               InlineKeyboardButton("Да",
                                                                                    "get_messages:yes")]]).to_dict()])
    await stateManager.set_state(update.callback_query.message.chat_id, ShelterRegistration.get_messages)


@dp.message_handler(StateFilter(ShelterRegistration.description))
async def shelter_get_messages_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.message.chat_id, "description", update.message.text)
    await bot.send_message(chat_id=update.message.chat_id,
                           text="Давать ли ссылку на ваш аккаунт в MAX человеку, который захочет забрать животное?",
                           attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Нет", "get_messages:0"),
                                                               InlineKeyboardButton("Да",
                                                                                    "get_messages:1")]]).to_dict()])
    await stateManager.set_state(update.chat_id, ShelterRegistration.get_messages)


async def get_messages_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "get_messages"


@dp.callback_query_handler(get_messages_callback)
async def shelter_finish_reg_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await bot.answer_callback(update.callback_query.callback_id, notification="Ваш ответ учтён.")

    shelter = await stateManager.get_all_data(update.callback_query.message.chat_id)
    get_messages = 1 if ("yes" == update.callback_query.payload.split(":")[1]) else 0
    data = {"name": shelter["name"], "location": shelter["location"], "address": shelter["address"],
            "get_messages": get_messages,
            "verified": 0}
    if "url" in shelter.keys():
        data["dobro_rf"] = shelter["url"]
    if "description" in shelter.keys():
        data["description"] = shelter["description"]

    await create_shelter(session, update.callback_query.from_user.user_id, **data)

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Приют успешно зарегистрирован! Вы сможете добавить животных с помощью команды /add, когда ваш приют будет верифицирован модераторами. Вам придёт уведомление.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


@dp.callback_query_handler(new_user_callback)
async def new_user_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    user = get_user_by_max_id(session, update.callback_query.from_user.user_id) is not None
    if user is None:
        await bot.answer_callback(update.callback_query.callback_id, notification="Регистрирую вас, как пользователя.")
    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Назовите город, в котором вы сейчас.")
    await stateManager.set_state(update.callback_query.message.chat_id, city)


@dp.message_handler(Command("search"))
@dp.message_handler(StateFilter(city))
async def city_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    user: User = await get_user_by_max_id(session, update.message.from_user.user_id)
    if user is None:
        if update.message.text == "/search":
            await bot.send_message(chat_id=update.message.chat_id,
                                   text="Вы ещё не зарегистрированы как пользователь. Зарегистрируйтесь по команде /start .")
            await stateManager.erase_state(update.message.chat_id)
            return
        await stateManager.set_data(update.message.chat_id, "city",
                                    update.message.text)
        await create_user(session, max_id=update.message.from_user.user_id,
                          location=update.message.text)
    else:
        if update.message.text != "/search":
            await stateManager.set_data(update.message.chat_id, "city",
                                        update.message.text)
            await update_user(session, user.id, location=update.message.text)
        else:
            await stateManager.set_data(update.message.chat_id, "city",
                                        user.location)
    await bot.send_message(chat_id=update.message.chat_id,
                           text="Какое животное вы бы хотели забрать?",
                           attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Собаку", "animal:dog"),
                                                               InlineKeyboardButton("Кошку", "animal:cat"),
                                                               InlineKeyboardButton("Другое", "animal:other")], [
                                                                  InlineKeyboardButton("Любое",
                                                                                       "animal:any")]]).to_dict()])


async def animal_choose_callback(update: Update):
    return update.callback_query.payload[:6] == "animal"


@dp.callback_query_handler(animal_choose_callback)
async def search_start_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    animal_type: str = update.callback_query.payload[7:]
    if animal_type == "any":
        await bot.answer_callback(update.callback_query.callback_id,
                                  "Теперь я могу приступить к поиску! Начнём?",
                                  [InlineKeyboardMarkup(
                                      [[InlineKeyboardButton("Поехали!", "search:_:any")]]).to_dict()])
        pets: list[Pet] = await get_pets_by_location(session,
                                                     await stateManager.get_data(update.callback_query.message.chat_id,
                                                                                 "city"))
        await stateManager.set_data(update.callback_query.message.chat_id, "pets", pets)
        await stateManager.set_data(update.callback_query.message.chat_id, "pets_index", 0)
    else:
        await bot.answer_callback(update.callback_query.callback_id,
                                  "Теперь я могу приступить к поиску! Начнём?",
                                  [InlineKeyboardMarkup(
                                      [[InlineKeyboardButton("Поехали!", f"search:_:{animal_type}")]]).to_dict()])
        pets: list[Pet] = await get_pets_by_location(session,
                                                     await stateManager.get_data(update.callback_query.message.chat_id,
                                                                                 "city"))
        await stateManager.set_data(update.callback_query.message.chat_id, "pets",
                                    [pet for pet in pets if pet.type == animal_type])
        await stateManager.set_data(update.callback_query.message.chat_id, "pets_index", 0)


async def search_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "search"


@dp.callback_query_handler(search_callback)
async def search_callback_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    if update.callback_query.payload.split(":")[1] == "like":

        pet: Pet = await get_pet_by_id(session, int(update.callback_query.payload.split(":")[3]))
        shelter: Shelter = await get_shelter_by_id(session, pet.shelter_id)
        await bot.send_message(user_id=shelter.max_id,
                               text=f"Пользователь по ссылке https://max.ru/{update.callback_query.from_user.user_id} заинтересовался {pet.name}.\n\nЯ отправил ему ваш адрес и контакт.\nНажмите принять, чтобы отправить согласие на посещение, или проигнорируйте, если вы не согласны.",
                               attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("принять",
                                                                                        f"accept:{update.callback_query.from_user.user_id}:{pet.id}")]]).to_dict()])
        await bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text=f"Вы можете встретиться с вашим будущим лучшим другом по адресу:\n{shelter.address}\n\nМы оповестили приют о вашей заинтересованности. Ссылка на ваш профиль была отправлена ему.{f"\n\nТакже, вы можете сами связаться с приютом по ссылке: https://max.ru/{shelter.max_id}" if shelter.get_messages else ""}"
        )
    pets: list[Pet] = await stateManager.get_data(update.callback_query.message.chat_id, "pets")
    pets_index: int = await stateManager.get_data(update.callback_query.message.chat_id, "pets_index")

    if pets_index < len(pets):
        pet: Pet = pets[pets_index]

        animal_types: dict[str, str] = {
            "dog": "Собака",
            "cat": "Кошка",
            "other": "Животное"
        }
        search_type: str = update.callback_query.payload.split(":")[2]

        # anketa = {"id": 123,
        #           "gender": 0,
        #           "animal": "Cобака",
        #           "name": "Бобик",
        #           "city": "Москва",
        #           "shelter": "Сокольнический",
        #           "img_token": "g4v4v45vvn4vgrgh3t3gri",
        #           "age": 16,
        #           "description": "Хорошая собачка"}

        await bot.answer_callback(
            update.callback_query.callback_id,
            f"{animal_types[pet.type]} {"Девочка" if not pet.gender else "Мальчик"} {pet.name}, {pet.age} - {pet.location}, приют {(await get_shelter_by_id(session, pet.shelter_id)).name}\n" \
            f"{pet.description}",
            [{"type": "image", "payload": {"token": pet.token}} for pet in (await get_photos_by_pet_id(session, pet.id))] + [
                InlineKeyboardMarkup([[InlineKeyboardButton("Лайк", f"search:like:{search_type}:{pet.id}"),
                                       InlineKeyboardButton("Дальше",
                                                            f"search:next:{search_type}:{pet.id}")]]).to_dict()])
        await stateManager.set_data(update.callback_query.message.chat_id, "pets_index", pets_index + 1)
    else:
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Животные кончились в вашем городе. Пожалуйста, попробуйте позднее или выберите другой город, зарегистрировавшись заного через /start .")
        await stateManager.erase_state(update.callback_query.message.chat_id)


async def accept_user_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "accept"


@dp.callback_query_handler(accept_user_callback)
async def accept_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter: Shelter = await get_shelter_by_max_id(session, update.callback_query.from_user.user_id)
    pet: Pet = await get_pet_by_id(session, int(update.callback_query.payload.split(":")[2]))
    await bot.send_message(user_id=int(update.callback_query.payload.split(":")[1]),
                           text=f"Вы можете встретиться с вашим будущим лучшим другом {pet.name} по адресу:\n{shelter.address}\n\nМы оповестили приют о вашей заинтересованности. Ссылка на ваш профиль была отправлена ему.{f"\n\nТакже, вы можете сами связаться с приютом по ссылке: https://max.ru/{shelter.max_id}" if shelter.get_messages else ""}"
                           )


@dp.message_handler(Command("moderation"))
async def start_moderation_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    if update.message.from_user.user_id in moderators:
        await bot.send_message(chat_id=update.message.chat_id,
                               text="Ваш статус модератора подтверждён. Приступаем к модерации?",
                               attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Поехали",
                                                                                        f"moderation-{update.message.from_user.user_id}:_")]]).to_dict()])


async def moderation_callback(update: Update):
    return (update.callback_query.payload.split(":")[0].split("-")[0] == "moderation") and (
            update.callback_query.payload.split(":")[0].split("-")[1] in moderators)


@dp.callback_query_handler(moderation_callback)
async def moderaion_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    if update.callback_query.payload.split(":")[1] == "_":
        shelters: list[Shelter] = await get_shelters_without_verification(session)
        await stateManager.set_data(update.callback_query.message.chat_id, "shelters",
                                    [s for s in shelters if s.verified == 1 and (s.dobro_rf or s.get_messages)])
        await stateManager.set_data(update.callback_query.message.chat_id, "shelters_index", 0)
    elif update.callback_query.payload.split(":")[1] == "like":
        shelter: Shelter = await get_shelter_by_id(session, int(update.callback_query.payload.split(":")[2]))
        await update_shelter(session, shelter.id, verified=1)
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Приют верифицирован.")

    shelters: list[Shelter] = await stateManager.get_data(update.callback_query.message.chat_id, "shelters")
    shelters_index: int = await stateManager.get_data(update.callback_query.message.chat_id, "shelters_index")
    if shelters_index < len(shelters):
        moderator_id: int = int(update.callback_query.payload.split(":")[0].split("-")[1])
        shelter: Shelter = shelters[shelters_index]

        await bot.answer_callback(
            update.callback_query.callback_id,
            f"Приют {shelter.name}, {shelter.address}\n" \
            f"{shelter.description}\n{f"url: {shelter.dobro_rf}" if shelter.dobro_rf else ""}",
            [InlineKeyboardMarkup([[InlineKeyboardButton("Одобрить", f"moderation-{moderator_id}:like:{shelter.id}"),
                                    InlineKeyboardButton("Отправить замечание", f"warn:{shelter.id}")]]).to_dict()])
    else:
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Все приюты верифицированы.")


async def moderation_warn_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "warn"


@dp.callback_query_handler(moderation_warn_callback)
async def warn_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Напишите замечание, которое будет отправлено приюту.")
    await stateManager.set_state(update.callback_query.message.chat_id, warn)
    await stateManager.set_data(update.callback_query.message.chat_id, "shelter_id",
                                update.callback_query.payload.split(":")[1])


@dp.message_handler(StateFilter(warn))
async def send_warn_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter_id = await stateManager.get_data(update.message.chat_id, "shelter_id")
    shelter = await get_shelter_by_id(session, shelter_id)
    await update_shelter(session, shelter.id, verified=-1)
    await bot.send_message(chat_id=shelter.max_id,
                           text=f"Модератор передал вам сообщение:\n\n{update.message.text}")
    await bot.send_message(chat_id=update.message.chat_id,
                           text="Сообщение отправлено приюту. Перейти к верификации приютов?",
                           attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Да",
                                                                                    f"moderation-{update.message.from_user.user_id}:next")]]).to_dict()])


@dp.message_handler(Command("shelter"))
async def shelter_settings_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = get_shelter_by_max_id(session, update.message.from_user.user_id)
    if shelter is None:
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Вы не зарегистрированы в качестве приюта. Чтобы зарегистрироваться, введите /start .")
    else:
        await bot.send_message(chat_id=update.message.chat_id,
                               text="Настройки приюта",
                               attachments=[InlineKeyboardMarkup(
                                   [[InlineKeyboardButton("Изменить описание", "shelter-change:description")],
                                    [InlineKeyboardButton("Изменить название", "shelter-change:name")],
                                    [InlineKeyboardButton("Изменить адрес", "shelter-change:address")],
                                    [InlineKeyboardButton("Изменить ссылку", "shelter-change:url")],
                                    [InlineKeyboardButton("Отправка профиля", "shelter-change:get_messages")],
                                    # [InlineKeyboardButton("Изменить город", "shelter-change:city")],
                                    [InlineKeyboardButton("Добавить животное", "add_pet")],
                                    [InlineKeyboardButton("Проверить верификацию", "shelter-change:verification")],
                                    [InlineKeyboardButton("Удалить приют", "shelter-change:delete")]]
                               ).to_dict()])


async def shelter_change_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "shelter-change"


@dp.callback_query_handler(shelter_change_callback)
async def shelter_change_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    command: str = update.callback_query.payload.split(":")[1]

    match command:
        case "description":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте новое описание приюта. Если вы хотите оставить его пустым, нажмите пусто.",
                                   attachments=[InlineKeyboardMarkup(
                                       [[InlineKeyboardButton("Пусто", "desc-change")]]).to_dict()])
            await stateManager.set_state(ShelterChange.description)
        case "name":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте новое название приюта.")
            await stateManager.set_state(ShelterChange.name)
        case "address":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте новый адрес приюта.")
            await stateManager.set_state(ShelterChange.address)
        case "url":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте новую ссылку на страницу приюта на dobro.ru . Если страницы нет, нажмите пусто.",
                                   attachments=[
                                       InlineKeyboardMarkup([[InlineKeyboardButton("Пусто", "url-change")]]).to_dict()])
            await stateManager.set_state(ShelterChange.url)
        case "get_messages":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Давать ли ссылку на ваш аккаунт в MAX человеку, который захочет забрать животное?",
                                   attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Нет",
                                                                                            "get_messages-change:0"),
                                                                       InlineKeyboardButton("Да",
                                                                                            "get_messages-change:1")]]).to_dict()])
            await stateManager.set_state(ShelterChange.get_messages)

        case "delete":
            shelter = await get_shelter_by_id(session, update.callback_query.from_user.user_id)
            await delete_shelter_by_max_id(session, shelter.max_id)

        case "verification":
            shelter = await get_shelter_by_id(session, update.callback_query.from_user.user_id)
            shelter_verification = shelter.verified
            if shelter_verification:
                await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                       text="Вы верифицированы")
            elif shelter_verification == -1:
                await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                       text="Ваш приют отклонен, измените данные")
            else:
                await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                       text="Вы еще не верифицированы")


@dp.message_handler(StateFilter(ShelterChange.name))
async def change_shelter_name_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = await get_shelter_by_max_id(session, update.message.from_user.user_id)
    if shelter is not None:
        name = (await stateManager.get_all_data(update.message.chat_id))["name"]
        await update_shelter(session, shelter.id, verified=0, name=name)

    await bot.send_message(chat_id=update.message.chat_id,
                           text="Имя изменено.")
    await stateManager.erase_state(update.message.chat_id)


@dp.message_handler(StateFilter(ShelterChange.address))
async def change_shelter_address_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = await get_shelter_by_max_id(session, update.message.from_user.user_id)
    if shelter is not None:
        address = (await stateManager.get_all_data(update.message.chat_id))["address"]
        await update_shelter(session, shelter.id, verified=0, address=address)

    await bot.send_message(chat_id=update.message.chat_id,
                           text="Адрес изменён.")
    await stateManager.erase_state(update.message.chat_id)


async def desc_change_callback(update: Update):
    return update.callback_query.payload == "desc-change"


@dp.callback_query_handler(desc_change_callback)
async def desc_null_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = await get_shelter_by_max_id(session, update.callback_query.from_user.user_id)
    if shelter is not None:
        await update_shelter(session, shelter.id, description='')

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Описание изменено.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


async def url_change_callback(update: Update):
    return update.callback_query.payload == "url-change"


@dp.callback_query_handler(url_change_callback)
async def url_null_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = await get_shelter_by_max_id(session, update.callback_query.from_user.user_id)
    if shelter is not None:
        await update_shelter(session, shelter.id, dobro_rf='')

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Ссылка на страницу изменена.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


@dp.message_handler(StateFilter(ShelterChange.description))
async def desc_null_st_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = await get_shelter_by_max_id(session, update.message.from_user.user_id)
    if shelter is not None:
        description = (await stateManager.get_all_data(update.message.chat_id))["description"]
        await update_shelter(session, shelter.id, description=description, verified=0)
    await bot.send_message(chat_id=update.message.chat_id,
                           text="Описание изменено.")
    await stateManager.erase_state(update.message.chat_id)


@dp.message_handler(StateFilter(ShelterChange.url))
async def url_null_st_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = await get_shelter_by_max_id(session, update.message.from_user.user_id)
    if shelter is None:
        await bot.send_message(chat_id=update.message.chat_id,
                               text="Вы не зарегистрированы в качестве приюта. Чтобы зарегистрироваться, введите /start .")
    else:
        shelter = await stateManager.get_all_data(update.message.chat_id)
        await update_shelter(session, update.message.from_user.user_id, verified=0, dobro_rf=shelter["url"])

        await bot.send_message(chat_id=update.message.chat_id,
                               text="Ссылка на страницу изменена.")
        await stateManager.erase_state(update.message.chat_id)


async def change_get_messages_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "get_messages-change"


@dp.callback_query_handler(change_get_messages_callback)
async def get_messages_change_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    get_messages: int = int(update.callback_query.payload.split(":")[1])

    shelter = await get_shelter_by_max_id(session, update.callback_query.from_user.user_id)
    if shelter is not None:
        shelter_id = shelter.id
        await update_shelter(session, shelter_id, get_messages=bool(get_messages))
    else:
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Вы не зарегистрированы в качестве приюта. Чтобы зарегистрироваться, введите /start .")

    await stateManager.erase_state(update.callback_query.message.chat_id)


async def add_pet_callback(update: Update):
    return update.callback_query.payload == "add_pet"


@dp.message_handler(Command("add"))
@dp.callback_query_handler(add_pet_callback)
async def add_pet_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    update.chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    await bot.send_message(chat_id=update.chat_id,
                           text="Выберите тип животного.",
                           attachments=[InlineKeyboardMarkup(
                               [[InlineKeyboardButton("Собака", "pet:dog"), InlineKeyboardButton("Кошка", "pet:cat")],
                                [InlineKeyboardButton("Другой", "pet:other")]]).to_dict()])
    await stateManager.set_state(update.chat_id, AnimalRegistration._type)


async def add_pet_type_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "pet"


@dp.callback_query_handler(add_pet_type_callback)
async def add_pet_type_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.callback_query.message.chat_id, "pet_type",
                                update.callback_query.payload.split(":")[1])

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Отправьте имя животного.")
    await stateManager.set_state(update.callback_query.message.chat_id, AnimalRegistration.name)


@dp.message_handler(StateFilter(AnimalRegistration.name))
async def add_pet_name_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.message.chat_id, "pet_name", update.message.text)

    await bot.send_message(chat_id=update.message.chat_id,
                           text="Отправьте возраст животного.")
    await stateManager.set_state(update.message.chat_id, AnimalRegistration.age)


@dp.message_handler(StateFilter(AnimalRegistration.age))
async def add_pet_age_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.message.chat_id, "pet_age", update.message.text)

    await bot.send_message(chat_id=update.message.chat_id,
                           text="Выберите пол животного.",
                           attachments=[InlineKeyboardMarkup([[
                               InlineKeyboardButton("Мужской", "pet_gender:1"),
                               InlineKeyboardButton("Женский", "pet_gender:0"),
                           ]]).to_dict()])
    # await stateManager.set_state(update.message.chat_id, AnimalRegistration.gender)


async def pet_gender_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "pet_gender"


# @dp.message_handler(StateFilter(AnimalRegistration.gender))
@dp.callback_query_handler(pet_gender_callback)
async def add_pet_gender_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.callback_query.message.chat_id, "pet_gender",
                                bool(int(update.callback_query.payload.split(":")[1])))

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Отправьте описание животного. Если вы не хотите его добавлять, нажмите нет.",
                           attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Нет", "pet-desc")]]).to_dict()])
    await stateManager.set_state(update.callback_query.message.chat_id, AnimalRegistration.description)


async def add_null_pet_desc_callback(update: Update):
    return update.callback_query.payload == "pet-desc"


@dp.callback_query_handler(add_null_pet_desc_callback)
async def add_null_pet_desc_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Отправьте изображения животного. (Максимум 12). Если не будете прикреплять изображения, нажмите нет.",
                           attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Нет", "pet-media")]]).to_dict()])
    await stateManager.set_state(update.callback_query.message.chat_id, AnimalRegistration.media)


@dp.message_handler(StateFilter(AnimalRegistration.description))
async def add_pet_desc_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    await stateManager.set_data(update.message.chat_id, "pet_description", update.message.text)
    await bot.send_message(chat_id=update.message.chat_id,
                           text="Отправьте изображения животного. (Максимум 12). Если не будете прикреплять изображения, нажмите нет.",
                           attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Нет", "pet-media")]]).to_dict()])
    await stateManager.set_state(update.message.chat_id, AnimalRegistration.media)


@dp.message_handler(StateFilter(AnimalRegistration.media))
async def add_media_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter_id = (await get_shelter_by_max_id(session, update.message.from_user.user_id)).id
    if shelter_id is None:
        await bot.send_message(chat_id=update.message.chat_id,
                               text="Вы не зарегистрированы в качестве приюта. Чтобы зарегистрироваться, введите /start .")
    else:
        pet = await stateManager.get_all_data(update.message.chat_id)
        data = {"name": pet["pet_name"], "age": pet["pet_age"], "gender": bool(int(pet["pet_gender"])),
                "pet_type": pet["pet_type"]}
        location = (await get_shelter_by_max_id(session, update.message.from_user.user_id)).location
        if "description" in pet.keys():
            data["description"] = pet["description"]

        pet_id = (await create_pet(session, shelter_id=shelter_id, location=location, **data)).id

        for image in update.message.attachments:
            if image["type"] == "image":
                await create_photo(session, pet_id=pet_id, token=image["payload"]["token"])

        await bot.send_message(chat_id=update.message.chat_id,
                               text="Животное добавлено.")
    await stateManager.erase_state(update.message.chat_id)


async def add_none_media_callback(update: Update):
    return update.callback_query.payload == "pet-media"


@dp.callback_query_handler(add_none_media_callback)
async def add_none_media_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter_id = (await get_shelter_by_max_id(session, update.callback_query.from_user.user_id)).id
    if shelter_id is None:
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Вы не зарегистрированы в качестве приюта. Чтобы зарегистрироваться, введите /start .")
    else:
        pet = await stateManager.get_all_data(update.callback_query.message.chat_id)
        data = {"name": pet["pet_name"], "age": pet["pet_age"], "gender": bool(int(pet["pet_gender"])),
                "pet_type": pet["pet_type"]}
        location = (await get_shelter_by_max_id(session, update.callback_query.from_user.user_id)).location
        if "description" in pet.keys():
            data["description"] = pet["description"]

        await create_pet(session, shelter_id=shelter_id, location=location, **data)

        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Животное добавлено.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


@dp.message_handler(Command("pets"))
async def pets_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter: Shelter = (await get_shelter_by_max_id(session, update.message.from_user.user_id))
    if shelter is not None:
        if shelter.verified == 1:
            pets: list[Pet] = await get_pets_by_shelter_id(session, shelter.id)

            await stateManager.set_data(update.message.chat_id, "pets", pets)
            await stateManager.set_data(update.message.chat_id, "pets_index", 0)
            await bot.send_message(chat_id=update.message.chat_id,
                                   text="Что вы хотите сделать с питомцами?",
                                   attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Добавить", "add_pet"),
                                                                       InlineKeyboardButton("Изменить",
                                                                                            "pet_change_next")]]).to_dict()])
        else:
            await bot.send_message(chat_id=update.message.chat_id,
                                   text="Ваш приют не верифицирован.")

    else:
        await bot.send_message(chat_id=update.message.chat_id,
                               text="Вы не зарегистрированы как приют. Зарегистрируйтесь по команде /start .")


async def pet_change_next_callback(update: Update):
    return update.callback_query.payload == "pet_change_next"


@dp.callback_query_handler(pet_change_next_callback)
async def pets_change_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    shelter = await get_shelter_by_max_id(session, update.callback_query.from_user.user_id)
    if shelter and shelter.verified:
        pets_index: int = await stateManager.get_data(update.callback_query.message.chat_id, "pets_index")
        pets: list[Pet] = await stateManager.get_data(update.callback_query.message.chat_id, "pets")
        if pets_index < len(pets):
            pet: Pet = pets[pets_index]

            # anketa = {"id": 123,
            #           "gender": 0,
            #           "animal": "Cобака",
            #           "name": "Бобик",
            #           "city": "Москва",
            #           "shelter": "Сокольнический",
            #           "img_token": "g4v4v45vvn4vgrgh3t3gri",
            #           "age": 16,
            #           "description": "Хорошая собачка"}

            await bot.answer_callback(
                callback_id=update.callback_query.callback_id,
                text=f"{pet.type} {"Девочка" if not pet.gender else "Мальчик"} {pet.name}, {pet.age} - {pet.location}, приют {(await get_shelter_by_id(session, pet.shelter_id)).name}\n" \
                     f"{pet.description}",
                attachments=[{"type": "image", "payload": {"token": pet.token}} for pet in
                             (await get_photos_by_pet_id(session, pet.id))] + [InlineKeyboardMarkup([
                    [InlineKeyboardButton("Следующее животное", "pet_change_next")],
                    [InlineKeyboardButton("Изменить животное", "pet_change:start")],
                    [InlineKeyboardButton("Удалить животное", "pet_change:delete")]]).to_dict()])
            await stateManager.set_data(update.callback_query.message.chat_id, "pets_index", pets_index + 1)
        else:
            await bot.answer_callback(chat_id=update.callback_query.message.chat_id,
                                      text="Вы просмотрели всех животных.")
            await stateManager.erase_state(update.callback_query.message.chat_id)
    else:
        await bot.send_message(chat_id=update.callback_query.message.chat_id,
                               text="Ваш приют ещё не верифицирован. Проверьте статус верификации в настройках по команде /shelter.")


async def pet_change_callback(update: Update):
    return update.callback_query.payload.split(":")[0] == "pet_change"


@dp.callback_query_handler(pet_change_callback)
async def pet_change_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    command: str = update.callback_query.payload.split(":")[1]

    match command:
        case "start":
            await bot.answer_callback(update.callback_query.callback_id,
                                      attachments=[InlineKeyboardMarkup([
                                          [InlineKeyboardButton("Изменить описание", "pet_change:description")],
                                          [InlineKeyboardButton("Изменить имя", "pet_change:name")],
                                          [InlineKeyboardButton("Изменить возраст", "pet_change:age")],
                                          [InlineKeyboardButton("Изменить тип животного", "pet_change:type")],
                                          [InlineKeyboardButton("Изменить пол", "pet_change:gender")],
                                          [InlineKeyboardButton("Изменить фото", "pet_change:media")],
                                          # [InlineKeyboardButton("Изменить город", "shelter-change:city")]
                                          [InlineKeyboardButton("Удалить животное", "pet_change:delete")]]
                                      ).to_dict()])
        case "delete":
            data = await stateManager.get_all_data(update.callback_query.message.chat_id)
            pets: list[Pet] = data["pets"]
            pets_index: int = data["pets_index"]
            pet: Pet = pets[pets_index - 1]
            await delete_pet_by_id(session, pet.id)

            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Животное удалено.")

        case "type":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Выберите новый тип животного.",
                                   attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Собака",
                                                                                            "pet_change:new_type:dog"),
                                                                       InlineKeyboardButton("Кошка",
                                                                                            "pet_change:new_type:cat")],
                                                                      [InlineKeyboardButton("Другой",
                                                                                            "pet_change:new_type:other")]]).to_dict()])

        case "new_type":
            data = await stateManager.get_all_data(update.callback_query.message.chat_id)
            pets: list[Pet] = data["pets"]
            pets_index: int = data["pets_index"]
            pet: Pet = pets[pets_index - 1]
            await update_pet(session, pet.id, pet_type=update.callback_query.payload.split(":")[2])
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Тип изменён.")

        case "description":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте описание животного. Если вы хотите его убрать, нажмите нет.",
                                   attachments=[
                                       InlineKeyboardMarkup([[InlineKeyboardButton("Нет", "pet_change:null_desc")]])])
            await stateManager.set_state(update.callback_query.message.chat_id, AnimalChange.description)

        case "null_desc":
            data = await stateManager.get_all_data(update.callback_query.message.chat_id)
            pets: list[Pet] = data["pets"]
            pets_index: int = data["pets_index"]
            pet: Pet = pets[pets_index - 1]
            await update_pet(session, pet.id, description='')

            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Описание изменено.")
            await stateManager.erase_state(update.callback_query.message.chat_id)

        case "name":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте новое имя животного.")
            await stateManager.set_state(update.callback_query.message.chat_id, AnimalChange.name)

        case "age":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте возраст животного.")
            await stateManager.set_state(update.callback_query.message.chat_id, AnimalChange.age)

        case "media":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Отправьте фотографии животного. Если вы хотите их убрать, нажмите нет.",
                                   attachments=[
                                       InlineKeyboardMarkup([[InlineKeyboardButton("Нет", "pet_change:null_media")]])])
            await stateManager.set_state(update.callback_query.message.chat_id, AnimalChange.media)

        case "null_media":
            data = await stateManager.get_all_data(update.callback_query.message.chat_id)
            pets: list[Pet] = data["pets"]
            pets_index: int = data["pets_index"]
            pet: Pet = pets[pets_index - 1]

            photos = await get_photos_by_pet_id(session, pet.id)
            for photo in photos:
                await delete_photo_by_token(session, token=photo.token)

            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Фотографии изменены.")

            await stateManager.erase_state(update.callback_query.message.chat_id)

        case "gender":
            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Выберите новый пол животного.",
                                   attachments=[InlineKeyboardMarkup([[InlineKeyboardButton("Мужской",
                                                                                            "pet_change:new_gender:1"),
                                                                       InlineKeyboardButton("Женский",
                                                                                            "pet_change:new_gender:0")]]).to_dict()])

        case "new_gender":
            data = await stateManager.get_all_data(update.callback_query.message.chat_id)
            pets: list[Pet] = data["pets"]
            pets_index: int = data["pets_index"]
            pet: Pet = pets[pets_index - 1]
            await update_pet(session, pet.id, gender=bool(int(update.callback_query.payload.split(":")[2])))

            await bot.send_message(chat_id=update.callback_query.message.chat_id,
                                   text="Пол изменён.")


@dp.message_handler(StateFilter(AnimalChange.description))
async def pet_change_description_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    data = await stateManager.get_all_data(update.callback_query.message.chat_id)
    pets: list[Pet] = data["pets"]
    pets_index: int = data["pets_index"]
    pet: Pet = pets[pets_index - 1]

    await update_pet(session, pet.id, description=update.message.text)

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Описание изменено.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


@dp.message_handler(StateFilter(AnimalChange.name))
async def pet_change_name_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    data = await stateManager.get_all_data(update.callback_query.message.chat_id)
    pets: list[Pet] = data["pets"]
    pets_index: int = data["pets_index"]
    pet: Pet = pets[pets_index - 1]
    await update_pet(session, pet.id, name=update.message.text)

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Имя изменено.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


@dp.message_handler(StateFilter(AnimalChange.age))
async def pet_change_age_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    data = await stateManager.get_all_data(update.callback_query.message.chat_id)
    pets: list[Pet] = data["pets"]
    pets_index: int = data["pets_index"]
    pet: Pet = pets[pets_index - 1]

    await update_pet(session, pet.id, age=data["age"])

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Возраст изменён.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


@dp.message_handler(StateFilter(AnimalChange.media))
async def pet_change_media_handler(update: Update, bot: Bot, stateManager: StateManager, session):
    data = await stateManager.get_all_data(update.callback_query.message.chat_id)
    pets: list[Pet] = data["pets"]
    pets_index: int = data["pets_index"]
    pet: Pet = pets[pets_index - 1]
    photos = await get_photos_by_pet_id(session, pet.id)
    for photo in photos:
        await delete_photo_by_token(session, token=photo.token)
    for token in update.message.attachments:
        await create_photo(session, pet.id, token=token)

    await bot.send_message(chat_id=update.callback_query.message.chat_id,
                           text="Фотографии изменены.")
    await stateManager.erase_state(update.callback_query.message.chat_id)


async def main():
    session = await create_db()
    async with bot:
        dp._session = session
        await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
