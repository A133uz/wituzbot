from sqlalchemy import (String, BigInteger, 
                        ForeignKey, 
                        DateTime,TIMESTAMP,
                        Text, UniqueConstraint,
                        Index, Boolean)
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .enums import EventTypeEnum
from datetime import datetime
from typing import List

from app.database.database import as_engine
from .database import Base, str_100, str_25








class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id = mapped_column(BigInteger)
    
    name: Mapped[str_25] 
    surname: Mapped[str_25]
    email: Mapped[str_100] = mapped_column(nullable=False)
    org: Mapped[str_100] 
    
    registrations: Mapped[List["Registration"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
   
class Organizer(Base):
    __tablename__ = "organizers"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str_25] 
    login: Mapped[str] = mapped_column(nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str_100] = mapped_column(nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    #Relationships
    events: Mapped[List["Event"]] = relationship(back_populates="organizer")
    
class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str_100]
    desc: Mapped[str] = mapped_column(Text())
    type: Mapped[EventTypeEnum] = mapped_column(String(25), nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    location: Mapped[str_100]
    
    organizer_id: Mapped[int] = mapped_column(ForeignKey("organizers.id"))
    
    #Relationships
    organizer: Mapped["Organizer"] = relationship(back_populates="events")
    registrations: Mapped[List["Registration"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    
   
    
class Registration(Base):
    __tablename__ = "registrations"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    
    #Relationships
    user: Mapped["User"] = relationship(back_populates="registrations")
    event: Mapped["Event"] = relationship(back_populates="registrations")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'event_id', name='unique_user_event'),
        Index('idx_event_id', 'event_id'),
        Index('idx_user_id', 'user_id'),
    )
    
async def async_main():
    async with as_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   