from aiogram.types import (KeyboardButton, InlineKeyboardButton, 
                           InlineKeyboardMarkup, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder



menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Events"), KeyboardButton(text='My Events')],
    [KeyboardButton(text='My Profile'), KeyboardButton(text='Contacts')],
],  resize_keyboard=True)

async def create_registration_button(event_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Register", callback_data=f"register_{event_id}")
    
    return kb.as_markup()
    
    
        

