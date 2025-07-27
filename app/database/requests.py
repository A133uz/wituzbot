from .models import User, Registration, Event, Organizer
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
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
    
async def set_registration(event_id: int, tg_id: int):
    try:
        async with get_session() as session:
            registration = Registration(
            user_id=tg_id,
            event_id=event_id,
            created_at=datetime.now()
        )
        
        session.add(registration)
        await session.commit()
        return True, "Registration successful!"
    except IntegrityError:
        await session.rollback()
        return False, "Registration failed due to database constraint.", None
    except Exception as e:
        await session.rollback()
        return False, f"An error occurred: {str(e)}", None
                
        

