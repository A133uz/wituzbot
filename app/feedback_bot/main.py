from .config import FeedbackBotSettings
from aiogram import Dispatcher, Bot
from .handlers import feedback_router
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import configure_logging
from utils.metrics import get_metrics, COUNTER_BOT_STARTS

configure_logging(service_name='feedback-bot')
logger = logging.getLogger(__name__)

settings = FeedbackBotSettings()
dp = Dispatcher()
bot = Bot(token=settings.TG_TOKEN)

async def main():
    logger.info("🤖 Feedback bot service starting...")
    get_metrics().increment(COUNTER_BOT_STARTS)
    
    dp.include_router(feedback_router)
    logger.info("✅ Feedback bot handlers registered and polling started")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Feedback bot polling error: {e}", exc_info=True)
        raise
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Feedback bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Feedback bot crashed: {e}", exc_info=True)
        raise