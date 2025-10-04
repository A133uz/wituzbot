import asyncio
import uvicorn


from aiogram import Bot, Dispatcher
from app.database.models import async_main, Organizer
from app.database.database import get_session
from app.database.config import settings
from app.bot.handlers import router
from app.admin.utils import get_password_hash


from sqlalchemy import select


bot = Bot(token=settings.tg_token)
dp = Dispatcher()

async def start_server():
    config = uvicorn.Config("app.admin.main:app", host="0.0.0.0", port=8000, reload=True)
    server = uvicorn.Server(config)
    await server.serve()
    
async def start_bot():
    dp.include_router(router)
    await dp.start_polling(bot)
    

async def main():
    await async_main()
    async with get_session() as session:
        try:
            res = await session.execute(select(Organizer).filter(Organizer.is_superuser == True))
            superuser = res.first()
            if not superuser:
                initial_superuser = Organizer(
                    name=settings.admin_name,
                    login=settings.admin_login,
                    email=settings.admin_email,
                    password_hash=get_password_hash(settings.admin_pass),  # Change this!
                    is_superuser=settings.admin_is_superuser,
                    is_active=settings.admin_is_active
                )
                
                session.add(initial_superuser)
                await session.commit()
                print("Initial superuser created: login='admin', password='admin123'")
                print("Please change these credentials immediately!")
        finally:
            pass
    await asyncio.gather(start_server(), start_bot())
        
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("System has been stopped")