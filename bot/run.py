import asyncio, os

from aiogram import Bot, Dispatcher
from app.database.models import async_main
from app.handlers import router

from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.getenv("tg_token"))
dp = Dispatcher()

async def main():
    await async_main()
    dp.include_router(router)
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    asyncio.run(main())