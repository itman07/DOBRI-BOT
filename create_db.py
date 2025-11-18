from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy import select
import tracemalloc  # отслеживание ошибок связанных с памятью
import asyncio
from models import Base, User, Shelter, Pet, Photo


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_user(db: AsyncSession, max_id: int, location: str):
    """Создание нового пользователя"""
    db_user = User(max_id=max_id, location=location.lower())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_id(db: AsyncSession, user_id: int):
    """Получение пользователя по ID"""
    result = await db.get(User, user_id)
    return result


async def get_user_by_max_id(db: AsyncSession, max_id: int):
    """Получение пользователя по max_ID"""
    stmt = select(User).where(User.max_id == max_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def update_user(db: AsyncSession, user_id: int, max_id: int = None, location: str = None):
    """Обновление пользователя"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    if max_id is not None:
        user.max_id = max_id
    if location is not None:
        user.location = location.lower()

    await db.commit()
    await db.refresh(user)
    return user


async def delete_user_by_max_id(db: AsyncSession, max_id: int) -> bool:
    """Удаление пользователя"""
    user = await get_user_by_max_id(db, max_id)
    if user:
        await db.delete(user)
        await db.commit()
        return True
    return False


async def create_pet(db: AsyncSession, shelter_id: int, pet_type: str, name: str, age: int, location: str, gender: bool,
                     description: str = None):
    """Создание нового питомца"""

    args = {}
    if description is not None:
        args["description"] = description

    db_pet = Pet(shelter_id=shelter_id, type=pet_type, name=name, age=age, location=location, gender=gender, **args)
    db.add(db_pet)
    await db.commit()
    await db.refresh(db_pet)
    return db_pet


async def get_pet_by_id(db: AsyncSession, pet_id: int):
    """Получение питомца по ID"""
    result = await db.get(Pet, pet_id)
    return result


async def get_pets_by_shelter_id(db: AsyncSession, shelter_id: int):
    """Получение питомцев по ID приюта"""
    stmt = select(Pet).where(Pet.shelter_id == shelter_id)
    result = await db.execute(stmt)
    pets = result.scalars()
    return pets.all()


async def get_pets_by_location(db: AsyncSession, location: str):
    """Получение всех питомцев в городе"""
    stmt = select(Pet).where(Pet.location == location)
    result = await db.execute(stmt)
    pets = result.scalars()
    return pets.all()


async def update_pet(db: AsyncSession, sql_id: int, shelter_id: int = None, pet_type: str = None,
                     name: str = None, age: int = None, location: str = None, gender: bool = None,
                     description: str = None):
    """Обновление питомца"""
    pet = await get_pet_by_id(db, sql_id)
    if not pet:
        return None

    if description is not None:
        pet.description = description
    if gender is not None:
        pet.gender = gender
    if name is not None:
        pet.name = name
    if shelter_id is not None:
        pet.shelter_id = shelter_id
    if pet_type is not None:
        pet.pet_type = pet_type
    if age is not None:
        pet.age = age
    if location is not None:
        pet.location = location

    await db.commit()
    await db.refresh(pet)
    return pet


async def delete_pet_by_id(db: AsyncSession, pet_id: int) -> bool:
    """Удаление пользователя"""
    pet = await get_pet_by_id(db, pet_id)
    if pet:
        await db.delete(pet)
        await db.commit()
        return True
    return False


async def create_shelter(db: AsyncSession, max_id: int, name: str, address: str, location: str, get_messages: bool = 0,
                         verified: int = False, description: str = None, dobro_rf: str = None):
    """Создание нового приюта"""

    args = {}
    if description is not None:
        args["description"] = description
    if dobro_rf is not None:
        args["dobro_rf"] = dobro_rf

    db_shelter = Shelter(max_id=max_id, get_messages=get_messages, address=address, verified=verified,
                         name=name, location=location.lower(), **args)
    db.add(db_shelter)
    await db.commit()
    await db.refresh(db_shelter)
    return db_shelter


async def get_shelter_by_id(db: AsyncSession, shelter_id: int):
    """Получение приюта по ID"""
    result = await db.get(Shelter, shelter_id)
    return result


async def get_shelter_by_max_id(db: AsyncSession, max_id: int):
    """Получение приюта по max_ID"""
    stmt = select(Shelter).where(Shelter.max_id == max_id)
    result = await db.execute(stmt)
    shelter = result.scalar_one_or_none()
    return shelter


async def get_shelters_by_location(db: AsyncSession, location: str) -> list[Shelter]:
    """Получение всех питомцев в городе"""
    stmt = select(Shelter).where(Shelter.location == location)
    result = await db.execute(stmt)
    shelters = result.scalars().all()
    return shelters


async def get_shelters_without_verification(db: AsyncSession) -> list[Shelter]:
    stmt = select(Shelter).where(Shelter.verified == 0)
    result = await db.execute(stmt)
    shelters = result.scalars().all()
    return shelters


async def update_shelter(db: AsyncSession, sql_id: int, get_messages: bool = None, verified: int = None,
                         max_id: int = None, name: str = None, address: str = None, location: str = None,
                         description: str = None, dobro_rf: str = None):
    """Обновление приюта"""
    shelter = await get_shelter_by_id(db, sql_id)
    if not shelter:
        return None

    if get_messages is not None:
        shelter.get_messages = get_messages
    if verified is not None:
        shelter.verified = verified
    if max_id is not None:
        shelter.max_id = max_id
    if name is not None:
        shelter.name = name
    if address is not None:
        shelter.address = address
    if location is not None:
        shelter.location = location.lower()
    if description is not None:
        shelter.description = description
    if dobro_rf is not None:
        shelter.dobro_rf = dobro_rf

    await db.commit()
    await db.refresh(shelter)
    return shelter


async def delete_shelter_by_max_id(db: AsyncSession, max_id: int) -> bool:
    """Удаление приюта"""
    shelter = await get_shelter_by_max_id(db, max_id)
    if shelter:
        await db.delete(shelter)
        await db.commit()
        return True
    return False


async def create_photo(db: AsyncSession, pet_id: int, token: str):
    """Добавление фото"""
    db_photo = Photo(pet_id=pet_id, token=token)
    db.add(db_photo)
    await db.commit()
    await db.refresh(db_photo)
    return db_photo


async def get_photo_by_token(db: AsyncSession, token: str):
    stmt = select(Photo).where(Photo.token == token)
    result = await db.execute(stmt)
    photo = result.scalar_one_or_none()
    return photo


async def get_photos_by_pet_id(db: AsyncSession, pet_id: int):
    stmt = select(Photo).where(Photo.pet_id == pet_id)
    result = await db.execute(stmt)
    photos = result.scalars()
    return photos.all()


async def delete_photo_by_token(db: AsyncSession, token: str) -> bool:
    photo = get_photo_by_token(db, token)
    if photo:
        await db.delete(photo)
        await db.commit()
        return True
    return False


async def create_db() -> int:
    db_url = 'sqlite+aiosqlite:///database.db'
    tracemalloc.start()
    engine: AsyncEngine = create_async_engine(db_url, echo=True, future=True)
    async_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    await create_tables(engine)

    return async_session_local()
    # async with async_session_local() as session:
    #     """Тесты на будущее"""
    # user = await create_user(session, 'Artem', 777, 'Moscow Ramenki')
    # print(f"user created: {user}")
    # user = await update_user(session, 1, "Vova", 123, 'Perm')
    # print(user)
    # print(await delete_user_by_max_id(session, 123))
    # shelter = await create_shelter(session, 123, 'Dota', 'Moscow Parmenki', 'Moscow')

    # print(await delete_shelter_by_max_id(session, 123))
    # print('нифига')
    # print(await get_shelter_by_max_id(session, 78474215))
    # print("Test completed")
    # return 0


if __name__ == "__main__":
    asyncio.run(create_db())
