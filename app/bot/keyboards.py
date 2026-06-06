from aiogram.types import (KeyboardButton, InlineKeyboardButton, 
                           InlineKeyboardMarkup, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from ..database.requests import check_user_registration
from .localization import Language, t, get_display_language_name


def get_menu(lang: Language = Language.EN) -> ReplyKeyboardMarkup:
    """Get the main menu keyboard in the specified language."""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t("menu_browse", lang)), KeyboardButton(text=t("menu_registrations", lang))],
        [KeyboardButton(text=t("menu_profile", lang)), KeyboardButton(text=t("menu_contacts", lang))],
    ], resize_keyboard=True)


# Backwards compatibility
menu = get_menu()

async def create_registration_button(event_id: int, user_id: int, lang: Language = Language.EN) -> InlineKeyboardMarkup:
    is_regd = await check_user_registration(user_id, event_id)
    if is_regd:
        return await create_registered_button(event_id, lang)
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_register", lang), callback_data=f"register_{event_id}")
    return kb.as_markup()

async def create_skip_button(lang: Language = Language.EN) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_skip", lang), callback_data="skip_field")
    return kb.as_markup()

def bot_registration_kb(lang: Language = Language.EN) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text=t("problem_faced", lang)))
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)

async def create_registered_button(event_id: int, lang: Language = Language.EN):
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(
        text=t("btn_registered", lang),
        callback_data="already_registered",
        style="success"
    ))
    kb.add(InlineKeyboardButton(
        text=t("btn_unregister", lang),
        callback_data=f"unregister_{event_id}",
        style="danger"
    ))
    kb.adjust(2) 
    return kb.as_markup()

async def update_profile_keyboard(lang: Language = Language.EN):
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(
        text=t("profile_update_name", lang), 
        callback_data="update_name"
    ))
    kb.add(InlineKeyboardButton(
        text=t("profile_update_surname", lang), 
        callback_data="update_surname"
    ))
    kb.add(InlineKeyboardButton(
        text=t("profile_update_org", lang), 
        callback_data="update_org"
    ))
    kb.add(InlineKeyboardButton(
        text=t("profile_update_language", lang), 
        callback_data="select_language"
    ))
    kb.adjust(1)
    return kb.as_markup()


def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    """Get the language selection keyboard."""
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="English", callback_data="lang_en"))
    kb.add(InlineKeyboardButton(text="Русский", callback_data="lang_ru"))
    kb.add(InlineKeyboardButton(text="Uzbek", callback_data="lang_uz"))
    kb.adjust(1)
    return kb.as_markup()
    


    
    
        

