from datetime import datetime

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import declared_attr
from sqlalchemy import ForeignKey, func

from sqlalchemy import String, Integer
from typing import Optional


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'


class Shelter(Base):
    verified: Mapped[int] = mapped_column()  # 1/0 верифицирован/нет  -1 требует правок
    get_messages: Mapped[bool] = mapped_column()  # 1/0 можно писать/нет
    max_id: Mapped[int] = mapped_column(unique=True)

    name: Mapped[str] = mapped_column(String(256))
    address: Mapped[str] = mapped_column(String(1024))
    location: Mapped[str] = mapped_column(String(64))

    description: Mapped[Optional[str]] = mapped_column(String(1024))
    dobro_rf: Mapped[Optional[str]] = mapped_column(String(256))
    contact_url: Mapped[Optional[str]] = mapped_column(String(512))

    def __repr__(self):
        return (f"<Shelter(id={self.id}, verified={self.verified}, name={self.name}, adress={self.address},"
                f" description={self.description}, dobro_rf={self.dobro_rf})>")


class Pet(Base):
    shelter_id: Mapped[int] = mapped_column(ForeignKey("shelters.id"))
    location: Mapped[str] = mapped_column(ForeignKey("shelters.location"))

    type: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(32))
    age: Mapped[int] = mapped_column()
    gender: Mapped[bool] = mapped_column()

    description: Mapped[Optional[str]] = mapped_column(String(1024))

    def __repr__(self):
        return (f"<Pet(id={self.id}, shelter_id={self.shelter_id},"
                f" type={self.type}, name={self.name}, description={self.description})>")


class Photo(Base):
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"))
    token: Mapped[str] = mapped_column(String(2048))


class User(Base):
    max_id: Mapped[int] = mapped_column(unique=True)

    location: Mapped[str] = mapped_column(String(64))

    url: Mapped[str] = mapped_column(String(512))

    def __str__(self):
        return f"Ползователь {self.username} в городе {self.location} с макс айди {self.max_id} под номером {self.id}"


class Moderator(Base):
    max_id: Mapped[int] = mapped_column(unique=True)
    is_admin: Mapped[bool] = mapped_column()  # 1/0 админ/не админ
