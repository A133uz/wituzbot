import asyncio
import uvicorn


from aiogram import Bot, Dispatcher
from app.database.models import async_main
from app.database.config import settings
from app.bot.handlers import router


from dotenv import load_dotenv

load_dotenv()

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
    await asyncio.gather(start_server(), start_bot())
        
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("System has been stopped")