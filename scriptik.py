from app.bot.config import MainBotSettings
from app.database.database import async_session
import app.bot.keyboards as kb
import asyncio
from sqlalchemy import select
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from app.database.models import User

botsettings = MainBotSettings()

async def main():
    async with async_session() as ses:
        res = await ses.execute(select(User.telegram_id, User.name)) 
        rows = res.all()  

    bot = Bot(token=botsettings.TG_TOKEN)
    for row in rows:
        try:
            await bot.send_message(chat_id=row.telegram_id, text=f"""👋 Hi, {row.name}!

We have several news to share with you:
                               
🔄 The bot has been updated! If your menu hasn't refreshed yet, just tap /start to get the latest version.

------

UPDATE! Women in Tech Open Day: Full Programs — Now Online

We’ve made an important update ❗️ 

To make this event accessible to participants from across Uzbekistan — and beyond — we decided to move our Women in Tech Open Day fully ONLINE.

Now you can join from anywhere.

And that makes it even easier to explore everything we’ve built.

During this session, you will be able to:

• discover all Women in Tech programs in one place
• understand what each program offers
• learn how to apply and participate
• ask your questions directly to the team

We will present our full ecosystem of programs, including: AI Boost, AI by Microsoft, AI by AWS, Blockchain, Canva, Digital Safety and more.

Each program will be introduced by our team, so you can clearly understand where to start and what fits you best.

This session is designed as a simple entry point into tech — structured, practical, and open to everyone.

<b>Please, make sure you registered for the event. If you haven't done it yet, browse our events to find it.</b>

------

Before the event, you'll need to register on Women in Tech Hub — it only takes a minute! Here's how:


Head to https://wit-h.com/
Click <b>Become a Member</b> in the top right corner.
Fill in the form and activate your account.


That's it — you're all set! Thanks so much. 🎉
""",
        parse_mode="HTML", reply_markup=kb.menu)
        except TelegramForbiddenError:
            print(f"User {row.name} with telegram_id {row.telegram_id} has blocked the bot.")
        await asyncio.sleep(0.05)

    await bot.session.close()

asyncio.run(main())
