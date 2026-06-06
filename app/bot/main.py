from aiogram import Dispatcher, Bot
import asyncio
import logging
from .config import MainBotSettings
from .handlers import router

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import configure_logging
from utils.metrics import get_metrics, COUNTER_BOT_STARTS

configure_logging(service_name='main-bot')
logger = logging.getLogger(__name__)

settings = MainBotSettings()
dp = Dispatcher()
bot = Bot(token=settings.TG_TOKEN)

async def main():
    logger.info("🤖 Main bot service starting...")
    get_metrics().increment(COUNTER_BOT_STARTS)
    
    dp.include_router(router)
    logger.info("✅ Handlers registered and polling started")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}", exc_info=True)
        raise
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Main bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Main bot crashed: {e}", exc_info=True)
        raise
        