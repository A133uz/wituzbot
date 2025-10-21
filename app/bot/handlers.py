from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import asyncio
import logging
import re
from pydantic import ValidationError
from ..database.schemas import UserBase


from ..database.requests import (set_user, get_user, 
                                 get_events, get_users_events_from_db,
                                 set_registration, remove_registration,
                                 check_user_registration)
from . import keyboards as kb

router = Router()

logger = logging.getLogger(__name__)

reg_fields = {
    "name" : "what's your name?",
    "surname" : "what's your surname?",
    "email" : "what's your email?",
    "org" : "where do you work/study?"
}

ordered_fields = list(reg_fields.items())

class Registration(StatesGroup):
    awaiting_input = State()
    
@router.message(CommandStart())
async def cmd_start_registration(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    if user:
        await msg.answer("Welcome back!", reply_markup=kb.menu)
        return 
    await state.set_state(Registration.awaiting_input)
    await state.update_data(step=0, registration_data={})
    field, question = ordered_fields[0]
    await msg.answer(f"Welcome! Let's meet! {question}")
    
@router.message(Registration.awaiting_input)
async def process_input(msg: Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("step", 0)
    registration_data = data.get("registration_data", {})
    
    field, question = ordered_fields[step]
    value = msg.text.strip()
    
    if field == "email":
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, value):
            await msg.answer("Please enter a valid email address (example: user@email.com).")
            return
        registration_data[field] = value
    else:
        if value: 
            registration_data[field] = value
        else:
            await msg.answer("Please enter a valid data.")
            return
    
    if step+1 < len(ordered_fields):
        _, next_question = ordered_fields[step+1]
        await state.update_data(step=step+1, registration_data=registration_data)
        await msg.answer(next_question)
    else:
        try:
            registration_data["telegram_id"] = msg.from_user.id         
            await set_user(registration_data)
        except ValueError as e:
            await msg.answer(f"{str(e)}")
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
            f"{event.type.capitalize()}\n"
            f"📍 {event.location}"
        )
        
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
                    f"🏷 {event.type.title()}\n"
                )

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
            f"Occupation: {user.org}\n"
        )
        await msg.answer(
            text=user_profile
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
    f"Send a message to our feedback bot: @wituzfeedback_bot \n\n" 
    f"You can send:\n"
    f"• Text descriptions of the problem\n"
    f"• Screenshots or videos showing the issue\n"
    f"• Any files that might help us understand the bug\n\n"
    f"We appreciate your help in making our service better! 🙏",
    parse_mode='HTML')

        
@router.callback_query(F.data.startswith('register_'))
async def register_user(cb: CallbackQuery):
    status, msg = await set_registration(int(cb.data.split('_')[1]), cb.from_user.id)
    if status:
        updated_kb = await kb.create_registered_button(int(cb.data.split('_')[1]))
        await cb.message.edit_reply_markup(reply_markup=updated_kb)
        await cb.answer(msg, show_alert=True)
    else:
        await cb.answer(msg, show_alert=True)
        
@router.callback_query(F.data.startswith('unregister_'))
async def unregister_user(cb: CallbackQuery):
    event_id = int(cb.data.split('_')[1])
    status, msg = await remove_registration(cb.from_user.id, event_id)

    # Re-check registration status to inform keyboard generation
    is_regd = await check_user_registration(cb.from_user.id, event_id)

    # Only update keyboard if registration state really changed
    if status and not is_regd:
        # Show "Register" button now
        updated_kb = await kb.create_registration_button(event_id, cb.from_user.id)
        try:
            await cb.message.edit_reply_markup(reply_markup=updated_kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass  # Harmless—just ignore
            else:
                raise
        await cb.answer(msg, show_alert=True)
    else:
        await cb.answer(msg, show_alert=True)
        
@router.callback_query(F.data == "already_registered")
async def handle_already_registered(callback: CallbackQuery):
    await callback.answer("You are already registered for this event!", show_alert=True)
    
