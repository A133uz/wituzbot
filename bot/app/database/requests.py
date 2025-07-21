from .models import User, Registration, Event, async_session
from sqlalchemy import select, update, delete
from typing import Dict

async def set_user(reg_data: Dict):
    async with async_session() as session:
        user = User(**reg_data)
        session.add(user)
        await session.commit()
        
async def get_user(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_id))
        return user
            
        

