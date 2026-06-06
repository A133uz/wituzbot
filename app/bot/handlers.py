from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import asyncio
import logging
from pydantic import ValidationError
from .validators import (validate_email, validate_name_or_surname, 
                         validate_org
                        )
from .localization import Language, t, get_language_from_telegram_code, get_display_language_name, get_description_for_language

import sys
from pathlib import Path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from ..database.requests import (set_user, get_user, update_user, 
                                 get_events, get_users_events_from_db,
                                 set_registration, remove_registration,
                                 check_user_registration, get_event_by_id)
from . import keyboards as kb

router = Router()

logger = logging.getLogger(__name__)


class RegistrationState(StatesGroup):
    awaiting_input = State()
    
class EventRegistrationState(StatesGroup):
    waiting_for_answer = State()
    
class ProfileUpdateState(StatesGroup):
    awaiting_new_value = State()

# Helper to get the field prompts for a language
def get_reg_fields(lang: Language):
    return {
        "name": t("reg_name", lang),
        "surname": t("reg_surname", lang),
        "organization": t("reg_organization", lang),
    }

def get_ordered_fields(lang: Language):
    fields = get_reg_fields(lang)
    return list(fields.items())

@router.message(CommandStart())
async def cmd_start_registration(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    user_lang = Language.EN
    
    # Log the bot start event
    logger.info(f"User {msg.from_user.id} ({msg.from_user.username or 'unknown'}) sent /start")
    
    if user:
        user_lang = Language(user.language) if user.language else Language.EN
        menu = kb.get_menu(user_lang)
        logger.debug(f"User {msg.from_user.id} returned (existing registration)")
        await msg.answer(t("welcome_back", user_lang), reply_markup=menu)
        return
    
    # Determine language from Telegram user language code
    user_lang = get_language_from_telegram_code(msg.from_user.language_code)
    
    await state.set_state(RegistrationState.awaiting_input)
    await state.update_data(step=0, registration_data={}, language=user_lang.value)
    
    ordered_fields = get_ordered_fields(user_lang)
    field, question = ordered_fields[0]
    
    await msg.answer(t("reg_welcome", user_lang, question=question),
                     parse_mode="HTML")
    
@router.message(RegistrationState.awaiting_input)
async def process_input(msg: Message, state: FSMContext):
    data = await state.get_data()
    user_lang = Language(data.get("language", "en"))
    
    if msg.text == t("problem_faced", user_lang):
        await msg.answer(
            t("bug_report_msg", user_lang),
            parse_mode='HTML'
        )
        await state.clear()
        await state.set_state(RegistrationState.awaiting_input)
        await state.update_data(step=0, registration_data={}, language=user_lang.value)
        
        ordered_fields = get_ordered_fields(user_lang)
        first_field, first_question = ordered_fields[0]
        await msg.answer(first_question, parse_mode="HTML", reply_markup=kb.bot_registration_kb(user_lang))
        return
    
    step = data.get("step", 0)
    registration_data = data.get("registration_data", {})
    
    ordered_fields = get_ordered_fields(user_lang)
    field, question = ordered_fields[step]
    
    if not msg.text:
        await msg.answer(f"❌ {t('error_empty_value', user_lang)}")
        return
    
    value = msg.text.strip()
    
    try:
        validators = {
            "name": lambda v: validate_name_or_surname(v, "Name"),
            "surname": lambda v: validate_name_or_surname(v, "Surname"),
            "organization": validate_org
        }
        
        if field in validators:
            value = validators[field](value)
            
    except ValueError as e:
        await msg.answer(f"{str(e)}\n{t('error_empty_value', user_lang)}")
        return
    
    registration_data[field] = value
    
    if step + 1 < len(ordered_fields):
        next_field, next_question = ordered_fields[step + 1]
        await state.update_data(step=step + 1, registration_data=registration_data)
        
        await msg.answer(next_question, reply_markup=kb.bot_registration_kb(user_lang),
                         parse_mode="HTML")
    else:
        try:
            registration_data["telegram_id"] = msg.from_user.id 
            registration_data["telegram_username"] = msg.from_user.username
            registration_data["language"] = user_lang.value
            await set_user(registration_data)
            
            # Log successful registration
            logger.info(f"✅ User {msg.from_user.id} ({msg.from_user.username or 'unknown'}) completed registration | name={registration_data.get('name')} | org={registration_data.get('organization')} | lang={user_lang.value}")
            
            # Import metrics here to avoid circular import
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.metrics import get_metrics, COUNTER_REGISTRATIONS_SUCCESS
            get_metrics().increment(COUNTER_REGISTRATIONS_SUCCESS)
            
        except ValidationError as ve:
            logger.warning(f"Registration validation error for user {msg.from_user.id}: {ve}")
            err_msgs = "\n".join([f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()])
            await msg.answer(f"Some inputs are incorrect:\n{err_msgs}\n{t('error_empty_value', user_lang)}")
            await state.clear()
            await state.set_state(RegistrationState.awaiting_input)
            await state.update_data(step=0, registration_data={}, language=user_lang.value)
            
            ordered_fields = get_ordered_fields(user_lang)
            first_field, first_question = ordered_fields[0]
            await msg.answer(first_question, parse_mode="HTML", reply_markup=kb.bot_registration_kb(user_lang))
            return
        except Exception as e:
            logger.error(f"Registration failed for user {msg.from_user.id}: {e}", exc_info=True)
            await msg.answer(f"{str(e)}")
            return 
        
        menu = kb.get_menu(user_lang)
        await msg.answer(t("reg_complete", user_lang), reply_markup=menu)
        await state.clear()

# Dynamic message filters for menu items - accept all 3 languages
def menu_browse_filter(msg: Message):
    return msg.text in [t("menu_browse", lang) for lang in Language]

def menu_registrations_filter(msg: Message):
    return msg.text in [t("menu_registrations", lang) for lang in Language]

def menu_profile_filter(msg: Message):
    return msg.text in [t("menu_profile", lang) for lang in Language]

def menu_contacts_filter(msg: Message):
    return msg.text in [t("menu_contacts", lang) for lang in Language]

async def get_user_language(user_id: int) -> Language:
    """Get user's language preference or detect from Telegram."""
    user = await get_user(user_id)
    if user and user.language:
        return Language(user.language)
    return Language.EN

@router.message(F.func(menu_browse_filter))
async def get_events_list(msg: Message):
    user_id = msg.from_user.id
    user_lang = await get_user_language(user_id)
    all_events = await get_events()
    
    if not all_events:
        await msg.answer(t("no_events", user_lang))
        return
    
    for event in all_events:
        event_type_display = t(f"event_type_{event.type}", user_lang)
        datetime_str = event.local_datetime.strftime(t("event_datetime_format", user_lang))
        
        event_txt = (
            f"📅 <b>{event.title}</b>\n"
            f"🕐 {datetime_str}\n"
            f"🏷 {event_type_display.title()}\n"
            f"📍 {event.location}"
        )
        if event.image_url:
            await msg.answer_photo(
                photo=event.image_url,
                caption=event_txt[:1024],
                reply_markup=await kb.create_registration_button(event.id, user_id, user_lang),
                parse_mode="HTML"
            )
        else:
            await msg.answer(
                text=event_txt,
                reply_markup=await kb.create_registration_button(event.id, user_id, user_lang),
                parse_mode="HTML"
            )
        
@router.message(F.func(menu_registrations_filter))
async def get_users_events(msg: Message):
    try:
        user_tg_id = msg.from_user.id
        user_lang = await get_user_language(user_tg_id)
        users_events = await get_users_events_from_db(user_tg_id)

        if not users_events:
            await msg.answer(t("no_registrations", user_lang))
            return

        for event in users_events:
            event_type_display = t(f"event_type_{event.type}", user_lang)
            datetime_str = event.local_datetime.strftime(t("event_datetime_format", user_lang))
            event_desc = get_description_for_language(event.desc, user_lang)
            
            event_text = (
                f"📅 <b>{event.title}</b>\n\n"
                f"📝 {event_desc}\n"
                f"🕐 {datetime_str}\n"
                f"📍 {event.location}\n"
                f"🏷 {event_type_display.title()}\n"
            )

            if event.image_url:
                await msg.answer_photo(
                    photo=event.image_url,
                    caption=event_text[:1024],  
                    parse_mode="HTML"
                )
            else:
                await msg.answer(
                    text=event_text,
                    parse_mode="HTML"
                )
            await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in the handler: {e}")
        user_lang = await get_user_language(msg.from_user.id)
        await msg.answer(t("error_empty_value", user_lang))
        
@router.message(F.func(menu_profile_filter))
async def get_users_profile(msg: Message):
    try:
        user_tg_id = msg.from_user.id
        user = await get_user(user_tg_id)
        user_lang = Language(user.language) if user.language else Language.EN
        
        user_profile = (
            t("profile_header", user_lang) + "\n\n"
            + t("profile_first_name", user_lang, name=user.name) + "\n"
            + t("profile_last_name", user_lang, surname=user.surname) + "\n"
            + t("profile_organization", user_lang, organization=user.organization) + "\n"
            + t("profile_language", user_lang, language=get_display_language_name(user_lang)) + "\n"
        )
        await msg.answer(
            text=user_profile,
            parse_mode="HTML",
            reply_markup=await kb.update_profile_keyboard(user_lang)
        )
    except Exception as e:
        logger.error(f"Error in the handler: {e}")
        user_lang = await get_user_language(msg.from_user.id)
        await msg.answer(t("error_empty_value", user_lang), reply_markup=kb.get_menu(user_lang))

@router.callback_query(F.data == "update_name")
async def update_first_name(cb: CallbackQuery, state: FSMContext):
    try:
        user = await get_user(cb.from_user.id)
        user_lang = Language(user.language) if user.language else Language.EN
        
        if not user:
            await cb.answer(t("error_invalid_field", user_lang), show_alert=True)
            return
        
        await state.set_state(ProfileUpdateState.awaiting_new_value)
        await state.update_data(field_to_update="name", language=user_lang.value)
        
        await cb.message.answer(t("update_name_prompt", user_lang), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error starting name update: {e}")
        await cb.answer("Something went wrong", show_alert=True)

@router.callback_query(F.data == "update_surname")
async def update_surname(cb: CallbackQuery, state: FSMContext):
    try:
        user = await get_user(cb.from_user.id)
        user_lang = Language(user.language) if user.language else Language.EN
        
        if not user:
            await cb.answer(t("error_invalid_field", user_lang), show_alert=True)
            return
        
        await state.set_state(ProfileUpdateState.awaiting_new_value)
        await state.update_data(field_to_update="surname", language=user_lang.value)
        
        await cb.message.answer(t("update_surname_prompt", user_lang), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error starting surname update: {e}")
        await cb.answer("Something went wrong", show_alert=True)

@router.callback_query(F.data == "update_org")
async def update_organization(cb: CallbackQuery, state: FSMContext):
    try:
        user = await get_user(cb.from_user.id)
        user_lang = Language(user.language) if user.language else Language.EN
        
        if not user:
            await cb.answer(t("error_invalid_field", user_lang), show_alert=True)
            return
        
        await state.set_state(ProfileUpdateState.awaiting_new_value)
        await state.update_data(field_to_update="organization", language=user_lang.value)
        
        await cb.message.answer(t("update_org_prompt", user_lang), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error starting org update: {e}")
        await cb.answer("Something went wrong", show_alert=True)

@router.callback_query(F.data == "select_language")
async def select_language(cb: CallbackQuery):
    """Show language selection keyboard."""
    await cb.message.answer(
        t("select_language", Language.EN),
        reply_markup=kb.get_language_selection_keyboard()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("lang_"))
async def change_language(cb: CallbackQuery):
    """Handle language change."""
    lang_code = cb.data.split("_")[1]
    user_lang = Language(lang_code)
    
    # Update user language in database
    await update_user(cb.from_user.id, {"language": lang_code})
    
    # Send confirmation with refreshed menu in the new language
    await cb.message.answer(
        t("language_changed", user_lang, language=get_display_language_name(user_lang)),
        reply_markup=kb.get_menu(user_lang)
    )
    await cb.answer()

@router.message(ProfileUpdateState.awaiting_new_value)
async def process_new_value(msg: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("field_to_update")
    user_lang = Language(data.get("language", "en"))
    new_val = msg.text.strip() if msg.text else ''
    
    if not new_val:
        await msg.answer(t("error_empty_value", user_lang))
        return
    
    try:
        if field == "name":
            new_val = validate_name_or_surname(new_val, "Name")
        elif field == "surname":
            new_val = validate_name_or_surname(new_val, "Surname")
        elif field == "organization":
            new_val = validate_org(new_val)
        else:
            await msg.answer(t("error_invalid_field", user_lang))
            await state.clear()
            return
        
        update_data = {field: new_val}
        updated_user = await update_user(msg.from_user.id, update_data)
        
        if not updated_user:
            await msg.answer(t("error_invalid_field", user_lang), reply_markup=kb.get_menu(user_lang))
            await state.clear()
            return
        
        await msg.answer(t("profile_updated", user_lang), parse_mode="HTML")
        await state.clear()
    
    except ValueError as e:
        await msg.answer(f"{str(e)}\n{t('error_empty_value', user_lang)}")
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        await msg.answer(t("error_empty_value", user_lang), reply_markup=kb.get_menu(user_lang))
        await state.clear()

@router.message(F.func(menu_contacts_filter))
async def show_contacts(msg: Message):
    user_lang = await get_user_language(msg.from_user.id)
    await msg.answer(t("contacts_msg", user_lang), parse_mode='HTML')
          
@router.callback_query(F.data.startswith('register_'))
async def register_user(cb: CallbackQuery, state: FSMContext):
    event_id = int(cb.data.split('_')[1])
    event = await get_event_by_id(event_id)
    user = await get_user(cb.from_user.id)
    user_lang = Language(user.language) if user.language else Language.EN
    
    pending_fields = []
    prompts = {}

    if getattr(event, "requires_email", False):
        pending_fields.append("email")
        prompts["email"] = t("email_prompt", user_lang)
    if getattr(event, "registration_question", None):
        pending_fields.append("registration_question")
        prompts["registration_question"] = t("custom_question_prompt", user_lang, question=event.registration_question)

    if pending_fields:
        current_field = pending_fields.pop(0)
        prompt = prompts[current_field]
        await cb.message.answer(prompt)
        await state.set_state(EventRegistrationState.waiting_for_answer)
        await state.update_data(
            event_id=event_id,
            pending_fields=pending_fields,
            prompts=prompts,
            current_field=current_field,
            answers={},
            language=user_lang.value
        )
    else:
        status, msg_code = await set_registration(event_id, cb.from_user.id)
        msg_text = t(msg_code, user_lang) if status else t(msg_code, user_lang)
        
        if status:
            logger.info(f"✅ User {cb.from_user.id} registered for event {event_id}")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.metrics import get_metrics, COUNTER_REGISTRATIONS_SUCCESS
            get_metrics().increment(COUNTER_REGISTRATIONS_SUCCESS)
            
            updated_kb = await kb.create_registered_button(event_id, user_lang)
            await cb.message.edit_reply_markup(reply_markup=updated_kb)
        else:
            logger.warning(f"Registration failed for user {cb.from_user.id} on event {event_id}: {msg_code}")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.metrics import get_metrics, COUNTER_REGISTRATIONS_FAILED
            get_metrics().increment(COUNTER_REGISTRATIONS_FAILED)
        
        await cb.answer(msg_text, show_alert=True)
        
@router.callback_query(F.data.startswith('unregister_'))
async def unregister_user(cb: CallbackQuery):
    event_id = int(cb.data.split('_')[1])
    user = await get_user(cb.from_user.id)
    user_lang = Language(user.language) if user.language else Language.EN
    
    status, msg_code = await remove_registration(cb.from_user.id, event_id)
    msg_text = t(msg_code, user_lang) if status else t(msg_code, user_lang)
    
    is_regd = await check_user_registration(cb.from_user.id, event_id)

    if status and not is_regd:
        updated_kb = await kb.create_registration_button(event_id, cb.from_user.id, user_lang)
        try:
            await cb.message.edit_reply_markup(reply_markup=updated_kb)
        except TelegramBadRequest as e:
            pass
        await cb.answer(msg_text, show_alert=True)
    else:
        await cb.answer(msg_text, show_alert=True)
        
@router.callback_query(F.data == "already_registered")
async def handle_already_registered(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    user_lang = Language(user.language) if user.language else Language.EN
    await callback.answer(t("already_registered", user_lang), show_alert=True)
    
@router.callback_query(F.data == "skip_field")
async def handle_skip_question(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_lang = Language(data.get("language", "en"))
    pending_fields = data.get("pending_fields", [])
    prompts = data.get("prompts", {})
    current_field = data.get("current_field")
    answers = data.get("answers", {})
    event_id = data.get("event_id")
    user_id = cb.from_user.id

    if current_field == "email":
        answers["email"] = None
    elif current_field == "registration_question":
        answers["answer"] = None

    if pending_fields:
        next_field = pending_fields.pop(0)
        await cb.message.answer(prompts[next_field])
        await state.update_data(
            pending_fields=pending_fields,
            current_field=next_field,
            answers=answers
        )
        await cb.answer()
    else:
        reg_email = answers.get("email")
        reg_answer = answers.get("answer")
        status, msg_code = await set_registration(event_id, user_id, email=reg_email, answer=reg_answer)
        msg_text = t(msg_code, user_lang) if status else t(msg_code, user_lang)
        
        if status:
            logger.info(f"✅ User {user_id} registered for event {event_id} (with answers)")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.metrics import get_metrics, COUNTER_REGISTRATIONS_SUCCESS
            get_metrics().increment(COUNTER_REGISTRATIONS_SUCCESS)
        else:
            logger.warning(f"Registration failed for user {user_id} on event {event_id}: {msg_code}")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.metrics import get_metrics, COUNTER_REGISTRATIONS_FAILED
            get_metrics().increment(COUNTER_REGISTRATIONS_FAILED)
        
        await cb.message.answer(msg_text)
        await state.clear()
        await cb.answer()
    
@router.message(EventRegistrationState.waiting_for_answer)
async def handle_waiting_for_answer(msg: Message, state: FSMContext):
    data = await state.get_data()
    user_lang = Language(data.get("language", "en"))
    pending_fields = data.get("pending_fields", [])
    prompts = data.get("prompts", {})
    current_field = data.get("current_field")
    answers = data.get("answers", {})
    event_id = data.get("event_id")
    user_id = msg.from_user.id

    reply = msg.text.strip() if msg.text else ""

    if current_field == "email":
        try:
            answers["email"] = validate_email(reply)
        except ValueError as e:
            await msg.answer(f"{str(e)}\n{t('btn_skip', user_lang)}")
            return
    elif current_field == "registration_question":
        answers["answer"] = reply if reply else None

    if pending_fields:
        next_field = pending_fields.pop(0)
        await msg.answer(prompts[next_field])
        await state.update_data(
            pending_fields=pending_fields,
            current_field=next_field,
            answers=answers
        )
    else:
        reg_email = answers.get("email")
        reg_answer = answers.get("answer")
        status, msg_code = await set_registration(event_id, user_id, email=reg_email, answer=reg_answer)
        msg_text = t(msg_code, user_lang) if status else t(msg_code, user_lang)
        
        if status:
            logger.info(f"✅ User {user_id} registered for event {event_id} (after answering questions)")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.metrics import get_metrics, COUNTER_REGISTRATIONS_SUCCESS
            get_metrics().increment(COUNTER_REGISTRATIONS_SUCCESS)
        else:
            logger.warning(f"Registration failed for user {user_id} on event {event_id}: {msg_code}")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.metrics import get_metrics, COUNTER_REGISTRATIONS_FAILED
            get_metrics().increment(COUNTER_REGISTRATIONS_FAILED)
        
        await msg.answer(msg_text)
        await state.clear()
