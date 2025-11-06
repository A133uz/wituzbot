from .models import User, Registration, Event, Organizer
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from typing import Dict, Optional
from datetime import datetime, timezone

import logging

from .database import get_session
from .schemas import UserCreate, RegistrationCreate

logger = logging.getLogger(__name__)

async def set_user(reg_data: Dict):
    async with get_session() as session:
        user_schema = UserCreate(**reg_data)
        
        user = User(**user_schema.model_dump())
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
                .where(Event.date_time > datetime.now(timezone.utc))
                .order_by(Event.date_time)
            )
            return res.scalars().all()
    except Exception as e:
        print(f"db error: {e}")
        return []

async def get_event_by_id(event_id: int):
    try:
        async with get_session() as session:
            res = await session.execute(
                select(Event).where(Event.id == event_id)
            )
            return res.scalar_one_or_none()
    except Exception as e:
        print(f"db error: {e}")
        return 
    
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
    
async def set_registration(event_id: int, tg_id: int, answer: Optional[str] = None):
    async with get_session() as session:
        try:
            existing = await session.execute(
                select(Registration).where(
                    Registration.user_id == tg_id,
                    Registration.event_id == event_id
                )
            )
            if existing.scalars().first():
                return False, "You are already registered for this event!"
            reg_schema = RegistrationCreate(
                user_id=tg_id,
                event_id=event_id,
                created_at=datetime.now(),
                question_answer=answer
            )
            registration = Registration(**reg_schema.model_dump())
            session.add(registration)
            await session.commit()
            return True, "Registration successful!"
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Registration DB error: {e}")
            return False, "Registration failed due to database constraint."
        except ValueError as e:
            await session.rollback()
            return False, f"❌ Validation error: {str(e)}"
        except Exception as e:
            await session.rollback()
            return False, f"An error occurred: {str(e)}"
    
async def check_user_registration(tg_id: int, event_id: int) -> bool:
    try:
        async with get_session() as session:
            res = await session.execute(select(Registration).filter(
                Registration.user_id == tg_id, 
                Registration.event_id == event_id
            ))
            reg = res.scalar_one_or_none()
        return reg is not None
    except Exception as e:
        return False
        
async def remove_registration(tg_id: int, event_id: int):
    try:
        async with get_session() as session:
            res = await session.execute(select(Registration).filter(
                Registration.user_id == tg_id,
                Registration.event_id == event_id
            ))
            reg = res.scalar_one_or_none()
            if reg:
                await session.delete(reg)
                await session.flush()
                await session.commit()
                return True, "Successfully unregistered!"
    except IntegrityError:
        await session.rollback()
        return False, "Registration failed due to database constraint."
    except ValueError as e:
        await session.rollback()
        return False, f"❌ Validation error: {str(e)}"
    except Exception as e:
        await session.rollback()
        return False, f"An error occurred: {str(e)}"
        


