from aiogram.types import (KeyboardButton, InlineKeyboardButton, 
                           InlineKeyboardMarkup, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from ..database.requests import check_user_registration 


menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📅 Browse Events"), KeyboardButton(text="📝 My Registrations")],
    [KeyboardButton(text="👤 My Profile"), KeyboardButton(text='Contacts')],
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
    kb.button(text="Skip", callback_data="skip_field")
    
    return kb.as_markup()

def bot_registration_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="I faced a problem"))
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)

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

async def update_profile_keyboard():
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(
        text="Update First Name", 
        callback_data="update_name"
    ))
    kb.add(InlineKeyboardButton(
        text="Update Last Name", 
        callback_data="update_surname"
    ))
    kb.add(InlineKeyboardButton(
        text="Update Organization", 
        callback_data="update_org"
    ))
    kb.adjust(1)
    return kb.as_markup()
    


    
    
        

