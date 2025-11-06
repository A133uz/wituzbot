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
        return await create_registered_button(event_id)
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Register", callback_data=f"register_{event_id}")

    return kb.as_markup()

async def create_skip_button() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Skip", callback_data="skip_question")
    
    return kb.as_markup()

def contact_request_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("📱 Share my phone number", request_contact=True))
    return kb

async def create_registered_button(event_id: int):
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(
        text="✅ Registered",
        callback_data="already_registered"
    ))
    kb.add(InlineKeyboardButton(
        text="❌ Unregister", callback_data=f"unregister_{event_id}"
        ))

    kb.adjust(2) 
    return kb.as_markup()


    
    
        

