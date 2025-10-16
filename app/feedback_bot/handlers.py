from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart
from .config import FeedbackBotSettings

settings = FeedbackBotSettings()

feedback_router = Router()
bot = Bot(token=settings.tg_token)

@feedback_router.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer("Welcome to feedback bot!\n" 
                      "In case you got any offer or a bug while using our bot, send it here!\n"
                      "<b> Thanks a lot for helping improve bot! </b>",
                      parse_mode='HTML')
     
@feedback_router.message()
async def handle_feedback(msg: Message):
    admin_chat_id = settings.admin_chat_id
    
    if msg.text:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=msg.text
        )
    if msg.photo:
       await bot.send_photo(
           chat_id=admin_chat_id,
           photo=msg.photo[-1].file_id,
           caption=f"Feedback from {msg.from_user.full_name}: {msg.caption or ''}"
       )
    elif msg.video:
        await bot.send_video(
            chat_id=admin_chat_id,
            video=msg.video.file_id,
            caption=f"Feedback from {msg.from_user.full_name}: {msg.caption or ''}"
        )

    await msg.reply("Thank you for feedback!")
    
        