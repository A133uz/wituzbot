from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


from .database.requests import set_user, get_user

router = Router()

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
        await msg.answer("Welcome back!")
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
    registration_data[field] = msg.text
    
    if step+1 < len(ordered_fields):
        next_field, next_question = ordered_fields[step+1]
        await state.update_data(step=step+1, registration_data=registration_data)
        await msg.answer(next_question)
    else:
        try:
            registration_data["telegram_id"] = msg.from_user.id
            await set_user(registration_data)
        except ValueError as e:
            await msg.answer(f"{str(e)}")
            return 
        
        await msg.answer("You have been successfully registered!")
        await state.clear()