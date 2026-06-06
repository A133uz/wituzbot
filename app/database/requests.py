from .models import User, Registration, Event, Organizer
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from typing import Dict, Optional
from datetime import datetime, timezone

import logging

from .database import get_session
from .schemas import UserCreate, RegistrationCreate, UserUpdate

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
    
async def update_user(telegram_id: int, update_data: Dict) -> Optional[User]:
    """
    Update user profile
    
    Args:
        telegram_id: User's Telegram ID
        update_data: Dictionary with fields to update (e.g., {'name': 'New Name'})
    
    Returns:
        Updated User object or None if user not found
    """
    async with get_session() as session:
        # Get the user
        user = await session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )
        
        if not user:
            return None
        
        # Validate update data with schema
        user_update_schema = UserUpdate(**update_data)
        
        # Update only provided fields
        update_dict = user_update_schema.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(user, field, value)
        
        await session.commit()
        await session.refresh(user)
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
        now = datetime.now(timezone.utc)
        async with get_session() as session:
            res = await session.execute(
                select(Event)
                .join(Registration, Event.id == Registration.event_id)
                .where(Registration.user_id == tg_id,
                       Event.date_time >= now)
                .order_by(Event.date_time)
            )
            return res.scalars().all()
    except Exception as e:
        print(f"db error: {e}")
        return 
    
async def set_registration(event_id: int, tg_id: int, answer: Optional[str] = None, email: Optional[str] = None):
    async with get_session() as session:
        try:
            existing = await session.execute(
                select(Registration).where(
                    Registration.user_id == tg_id,
                    Registration.event_id == event_id
                )
            )
            if existing.scalars().first():
                logger.debug(f"User {tg_id} already registered for event {event_id}")
                return False, "registration_already_exists"
            
            reg_schema = RegistrationCreate(
                user_id=tg_id,
                event_id=event_id,
                created_at=datetime.now(),
                question_answer=answer,
                email=email
            )
            registration = Registration(**reg_schema.model_dump())
            session.add(registration)
            await session.commit()
            
            logger.debug(f"Registration created: user {tg_id} for event {event_id}")
            return True, "registration_successful"
            
        except IntegrityError as e:
            await session.rollback()
            logger.warning(f"Registration constraint error for user {tg_id}, event {event_id}: {e}")
            return False, "registration_error_constraint"
        except ValueError as e:
            await session.rollback()
            logger.warning(f"Registration validation error for user {tg_id}, event {event_id}: {e}")
            return False, "registration_error_validation"
        except Exception as e:
            await session.rollback()
            logger.error(f"Registration unexpected error for user {tg_id}, event {event_id}: {e}")
            return False, "registration_error_unknown"
    
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
                return True, "unregistration_successful"
    except IntegrityError:
        await session.rollback()
        return False, "unregistration_error_constraint"
    except ValueError as e:
        await session.rollback()
        return False, "unregistration_error_validation"
    except Exception as e:
        await session.rollback()
        return False, "unregistration_error_unknown"
        


