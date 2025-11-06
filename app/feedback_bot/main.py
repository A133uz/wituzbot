from .config import FeedbackBotSettings
from aiogram import Dispatcher, Bot
from .handlers import feedback_router
import asyncio

settings = FeedbackBotSettings()
dp = Dispatcher()
bot = Bot(token=settings.TG_TOKEN)

async def main():
    dp.include_router(feedback_router)
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("The bot has been stopped")