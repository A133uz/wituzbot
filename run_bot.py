import asyncio, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))


from aiogram import Bot, Dispatcher
from app.database.models import async_main
from app.database.config import settings
from app.bot.handlers import router


from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=settings.tg_token)
dp = Dispatcher()

async def main():
        await async_main()
        dp.include_router(router)
        await dp.start_polling(bot)
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot has been stopped")