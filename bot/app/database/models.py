from sqlalchemy import (String, BigInteger, 
                        ForeignKey, Enum, 
                        DateTime,TIMESTAMP)
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from .enums import EventTypeEnum
from datetime import datetime
from typing import List

from dotenv import load_dotenv

import os

load_dotenv()

engine = create_async_engine(url=os.getenv("db_url"), echo=True)

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass



class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id = mapped_column(BigInteger)
    
    name: Mapped[str] = mapped_column(String(25))
    surname: Mapped[str] = mapped_column(String(25))
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    org: Mapped[str] = mapped_column(String(100))
    
    registrations: Mapped[List["Registration"]] = relationship("Registration", backref="users")
    events: Mapped[list["Event"]] = relationship(
        "Event",
        secondary="registrations",  # name of association table
        back_populates="users",
        viewonly=True               # only for reading via this field
    )

class Organizer(Base):
    __tablename__ = "organizers"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(25))
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    
class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100))
    desc: Mapped[str] = mapped_column(String(512))
    type: Mapped[EventTypeEnum] = mapped_column(Enum(EventTypeEnum), name="event_type_enum",
                                                nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location: Mapped[str] = mapped_column(String(100))
    
    organizer_id: Mapped[int] = mapped_column(ForeignKey("organizers.id"))
    organizer: Mapped["Organizer"] = relationship()
    
    registrations: Mapped[List["Registration"]] = relationship("Registration", backref="events")
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="registrations",
        back_populates="events",
        viewonly=True
    )
    
class Registration(Base):
    __tablename__ = "registrations"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"),  nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    
async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   