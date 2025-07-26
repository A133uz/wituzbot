from .models import User, Registration, Event, Organizer
from sqlalchemy import select, update, delete
from typing import Dict
from datetime import datetime
import bcrypt, uuid

from .database import get_session

async def set_user(reg_data: Dict):
    async with get_session() as session:
        user = User(**reg_data)
        session.add(user)
        await session.commit()
        
async def get_user(tg_id):
    async with get_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        return user
    
async def get_events():
    try:
        async with get_session() as session:
            res = await session.execute(
                select(Event)
                .where(Event.date_time > datetime.now())
                .order_by(Event.date_time)
            )
            return res.scalars().all()
    except Exception as e:
        print(f"db error: {e}")
        return []
    
async def get_users_events_from_db(tg_id: int):
    try:
        async with get_session() as session:
            res = await session.execute(
                select(Event)
                .join(Registration, Event.id == Registration.event_id)
                .where(Registration.user_id == tg_id)
                .order_by(Event.date_time)
            )
            return res.scalars().all()
    except Exception as e:
        print(f"db error: {e}")
        return 
    
@staticmethod
async def create_organizer(username: str, email: str, name: str, 
                             password: str, is_superuser: bool = False) -> Organizer | None:
        """Create new organizer"""
        try:
            async with get_session() as session:
                hash_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                organizer = Organizer(
                    login=username,
                    email=email,
                    name=name,
                    password_hash=hash_password,
                    is_superuser=is_superuser,
                    is_active=True
                )
                session.add(organizer)
                await session.commit()
                await session.refresh(organizer)
                return organizer
        except Exception as e:
            print(f"Error creating organizer: {e}")
            return None

@staticmethod    
async def authenticate(login: str, password: str) -> int | None:
    async with get_session() as session:
        query = select(Organizer).filter_by(login=login, is_superuser=True)
        res = await session.scalars(query)
        obj = res.first()
        if not obj:
            return None
        if not bcrypt.checkpw(password.encode(), obj.password_hash.encode()):
            return None
        return obj.id
    
    
@staticmethod
async def change_pw(id: int, password: str) -> bool:
    try:
        async with get_session() as session:
            pw_hash = bcrypt.checkpw(password.encode(), bcrypt.gensalt()).decode()
            query = update(Organizer).where(Organizer.id.in_([id])).values(password_hash=pw_hash)
            await session.execute(query)
            await session.commit()
            return True
    except Exception as e:
        print(f"Error changing password: {e}")
        return False
                
        

