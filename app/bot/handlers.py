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
                         validate_org, validate_phone
                        )


from ..database.requests import (set_user, get_user, 
                                 get_events, get_users_events_from_db,
                                 set_registration, remove_registration,
                                 check_user_registration, get_event_by_id)
from . import keyboards as kb

router = Router()

logger = logging.getLogger(__name__)

reg_fields = {
    "name" : "What's your first name?",
    "surname" : "What's your last name?",
    "phone" : "📱 Please share your phone number using the button below:",
    "organization" : "Where do you work/study?"
}

ordered_fields = list(reg_fields.items())



class RegistrationState(StatesGroup):
    awaiting_input = State()
    
class EventRegistrationState(StatesGroup):
    waiting_for_answer = State()
    
@router.message(CommandStart())
async def cmd_start_registration(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if user:
        await msg.answer("Welcome back!", reply_markup=kb.menu)
        return 
    await state.set_state(RegistrationState.awaiting_input)
    await state.update_data(step=0, registration_data={})
    field, question = ordered_fields[0]
    await msg.answer(f"Welcome! Let's meet! {question}")
    
@router.message(RegistrationState.awaiting_input)
async def process_input(msg: Message, state: FSMContext):
    if msg.text == "I faced a problem":
        await msg.answer(
            "🐛 <b>Found a Bug? We Want to Hear About It!</b>\n\n"
            "Please contact our feedback bot: @womenintechuz_fb_bot\n"
            "Registration will restart.",
            parse_mode='HTML'
        )
        await state.clear()
        await state.set_state(RegistrationState.awaiting_input)
        await state.update_data(step=0, registration_data={})
        first_field, first_question = ordered_fields[0]
        await msg.answer(first_question)
        return
    
    data = await state.get_data()
    step = data.get("step", 0)
    registration_data = data.get("registration_data", {})
    
    field, question = ordered_fields[step]
    
    if field == "phone":
        if msg.contact:
            value = msg.contact.phone_number
        else:
            await msg.answer("❌ Please share your contact")
            return
    else:
        if not msg.text:
            await msg.answer(f"❌ Please enter your {field}.")
            return
        value = msg.text.strip()
        
    
               
    try:
        validators = {
            "name": lambda v: validate_name_or_surname(v, "Name"),
            "surname": lambda v: validate_name_or_surname(v, "Surname"),
            "phone": validate_phone,
            "organization": validate_org
        }
        
        if field in validators:
            value = validators[field](value)
            
            
    except ValueError as e:
        await msg.answer(f"{str(e)}\nPlease try again:")
        return
    
    registration_data[field] = value
        
    
    if step+1 < len(ordered_fields):
        next_field, next_question = ordered_fields[step+1]
        await state.update_data(step=step+1, registration_data=registration_data)
        
        if next_field == "phone":
            await msg.answer(next_question, reply_markup=kb.bot_registration_kb(include_contact=True))
        else:
            await msg.answer(next_question, reply_markup=kb.bot_registration_kb())
    else:
        try:
            registration_data["telegram_id"] = msg.from_user.id 
            registration_data["telegram_username"] = msg.from_user.username        
            await set_user(registration_data)
        except Exception as e:
            await msg.answer(f"{str(e)}")
            return 
        except ValidationError as ve:
            err_msgs = "\n".join([f"{err['loc'][0]}: {err['msg']}" for err in ve.errors()])
            await msg.answer(f"Some inputs are incorrect:\n{err_msgs}\nLet's try registration again.")
            await state.clear()
            await state.set_state(RegistrationState.awaiting_input)
            await state.update_data(step=0, registration_data={})
            first_field, first_question = ordered_fields[0]
            await msg.answer(first_question)
            return
        
        await msg.answer("You have been successfully registered!", reply_markup=kb.menu)
        await state.clear()
        
@router.message(F.text == "Events")
async def get_events_list(msg: Message):
    user_id = msg.from_user.id
    all_events = await get_events()
    
    if not all_events:
        await msg.answer("No upcoming events at the moment")
        return
    
    for event in all_events:
        event_txt = (
            f"📅 <b>{event.title}</b>\n"
            f"🕐 {event.local_datetime.strftime('%d.%m.%Y at %H:%M')}\n"
            f"🏷 {event.type.replace('_', ' ').title()}\n"
            f"📍 {event.location}"
        )
        if event.image_url:
            await msg.answer_photo(
                photo=event.image_url,
                caption=event_txt[:1024],
                reply_markup=await kb.create_registration_button(event.id, user_id),
                parse_mode="HTML"
            )
        else:
            await msg.answer(
                text=event_txt,
                reply_markup=await kb.create_registration_button(event.id, user_id),
                parse_mode="HTML"
            )
        
@router.message(F.text == "My Events")
async def get_users_events(msg: Message):
    try:
        user_tg_id = msg.from_user.id
        users_events = await get_users_events_from_db(user_tg_id)

        if not users_events:
            await msg.answer("You haven't registered at any event yet")
            return

        for event in users_events:
                event_text = (
                    f"📅 <b>{event.title}</b>\n"
                    f"📝 {event.desc}\n"
                    f"🕐 {event.local_datetime.strftime('%d.%m.%Y at %H:%M')}\n"
                    f"📍 {event.location}\n"
                    f"🏷 {event.type.replace('_', ' ').title()}\n"
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
        await msg.answer("❌ Something went wrong. Please try again later.")
        
@router.message(F.text == "My Profile")
async def get_users_profile(msg: Message):
    try:
        user_tg_id = msg.from_user.id
        user = await get_user(user_tg_id)
        user_profile = (
            f"Name: {user.name}\n"
            f"Surname: {user.surname}\n"
            f"Organization: {user.organization}\n"
        )
        await msg.answer(
            text=user_profile,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in the handler: {e}")
        await msg.answer("Something went wrong. Try again later")
        
@router.message(F.text == "Contacts")
async def show_contacts(msg: Message):
    await msg.answer(f"🐛 <b>Found a Bug? We Want to Hear About It!</b>\n\n"
    f"If you've encountered any issues or bugs while using our service, "
    f"please don't hesitate to report them! Your feedback helps us improve.\n\n"
    f"📝 <b>How to report:</b>\n"
    f"Send a message to our feedback bot: @womenintechuz_fb_bot \n\n" 
    f"You can send:\n"
    f"• Text descriptions of the problem\n"
    f"• Screenshots or videos showing the issue\n\n"
    f"We appreciate your help in making our service better! 🙏",
    parse_mode='HTML')
          
@router.callback_query(F.data.startswith('register_'))
async def register_user(cb: CallbackQuery, state: FSMContext):
    event_id = int(cb.data.split('_')[1])
    event = await get_event_by_id(event_id)
    pending_fields = []
    prompts = {}

    if getattr(event, "requires_email", False):
        pending_fields.append("email")
        prompts["email"] = "Please enter your email address (or tap 'Skip')."
    if getattr(event, "registration_question", None):
        pending_fields.append("registration_question")
        prompts["registration_question"] = f"📝 {event.registration_question}\n\nSend your answer, or tap 'Skip'."

    if pending_fields:
        current_field = pending_fields.pop(0)
        prompt = prompts[current_field]
        await cb.message.answer(prompt, reply_markup=await kb.create_skip_button())
        await state.set_state(EventRegistrationState.waiting_for_answer)
        await state.update_data(
            event_id=event_id,
            pending_fields=pending_fields,
            prompts=prompts,
            current_field=current_field,
            answers={}
        )
    else:
        status, msg = await set_registration(event_id, cb.from_user.id)
        if status:
            updated_kb = await kb.create_registered_button(event_id)
            await cb.message.edit_reply_markup(reply_markup=updated_kb)
        await cb.answer(msg, show_alert=True)
        
@router.callback_query(F.data.startswith('unregister_'))
async def unregister_user(cb: CallbackQuery):
    event_id = int(cb.data.split('_')[1])
    status, msg = await remove_registration(cb.from_user.id, event_id)

    
    is_regd = await check_user_registration(cb.from_user.id, event_id)

    
    if status and not is_regd:
        
        updated_kb = await kb.create_registration_button(event_id, cb.from_user.id)
        try:
            await cb.message.edit_reply_markup(reply_markup=updated_kb)
        except TelegramBadRequest as e:
            pass
        await cb.answer(msg, show_alert=True)
    else:
        await cb.answer(msg, show_alert=True)
        
@router.callback_query(F.data == "already_registered")
async def handle_already_registered(callback: CallbackQuery):
    await callback.answer("You are already registered for this event!", show_alert=True)
    
@router.callback_query(F.data == "skip_field")
async def handle_skip_question(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
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
        await cb.message.answer(prompts[next_field], reply_markup=await kb.create_skip_button())
        await state.update_data(
            pending_fields=pending_fields,
            current_field=next_field,
            answers=answers
        )
        await cb.answer()
    else:
        reg_email = answers.get("email")
        reg_answer = answers.get("answer")
        status, msg_text = await set_registration(event_id, user_id, email=reg_email, answer=reg_answer)
        await cb.message.answer(msg_text)
        await state.clear()
        await cb.answer()
    
@router.message(EventRegistrationState.waiting_for_answer)
async def handle_waiting_for_answer(msg: Message, state: FSMContext):
    data = await state.get_data()
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
            await msg.answer(str(e) + "\nPlease enter a valid email or tap 'Skip'.")
            return
    elif current_field == "registration_question":
        answers["answer"] = reply if reply else None

    if pending_fields:
        next_field = pending_fields.pop(0)
        await msg.answer(prompts[next_field], reply_markup=await kb.create_skip_button())
        await state.update_data(
            pending_fields=pending_fields,
            current_field=next_field,
            answers=answers
        )
    else:
        reg_email = answers.get("email")
        reg_answer = answers.get("answer")
        status, msg_text = await set_registration(event_id, user_id, email=reg_email, answer=reg_answer)
        await msg.answer(msg_text)
        await state.clear()
    

    
