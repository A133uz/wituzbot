from aiogram import Dispatcher, Bot
import asyncio
from .config import MainBotSettings
from .handlers import router

settings = MainBotSettings()
dp = Dispatcher()
bot = Bot(token=settings.tg_token)

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("The main bot has been stopped")
        