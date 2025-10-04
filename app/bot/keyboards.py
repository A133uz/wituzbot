from aiogram.types import (KeyboardButton, InlineKeyboardButton, 
                           InlineKeyboardMarkup, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ..database.requests import check_user_registration 


menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Events"), KeyboardButton(text='My Events')],
    [KeyboardButton(text='My Profile'), KeyboardButton(text='Contacts')],
],  resize_keyboard=True)

async def create_registration_button(event_id: int, user_id: int) -> InlineKeyboardMarkup:
    is_regd = await check_user_registration(user_id, event_id)
    if is_regd:
        return await create_registered_button()
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Register", callback_data=f"register_{event_id}")

    return kb.as_markup()

async def create_registered_button():
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(
        text="✅ Registered",
        callback_data="already_registered"
    ))
    return kb.as_markup()
    
    
        

