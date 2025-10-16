import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import AdminSettings
from database.database import get_session
from sqlalchemy import select
from database.models import Organizer
from .utils import get_password_hash

async def create_initial_superuser():
    settings = AdminSettings()
    
    async with get_session() as session:
        try:
            res = await session.execute(select(Organizer).filter(Organizer.is_superuser == True))
            superuser = res.first()
            if not superuser:
                initial_superuser = Organizer(
                    name=settings.admin_name,
                    login=settings.admin_login,
                    email=settings.admin_email,
                    password_hash=get_password_hash(settings.admin_pass),
                    is_superuser=settings.admin_is_superuser,
                    is_active=settings.admin_is_active
                )
                
                session.add(initial_superuser)
                await session.commit()
                print("Initial superuser created")
        except Exception as e:
            print(f"Error creating superuser: {e}")