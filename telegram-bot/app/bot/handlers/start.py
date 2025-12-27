"""Обработчик команды /start."""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud import get_user_by_telegram_id
from app.bot.states import RegistrationStates
from app.bot.keyboards.inline import get_main_menu_keyboard
from app.bot.utils.messages import Messages, UserStatus
from app.utils.logger import logger

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработка команды /start.
    
    Логика:
    - Новый пользователь → начало регистрации
    - Пользователь в процессе регистрации → возврат в текущий шаг
    - Зарегистрированный пользователь → главное меню
    """
    telegram_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    logger.info(f"User {telegram_id} (@{username}) started bot")
    
    # Проверяем, зарегистрирован ли пользователь
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if user:
        # Пользователь найден - очищаем состояние регистрации
        await state.clear()
        
        # Формируем статус пользователя
        has_api_key = bool(user.wb_api_key)
        has_table = bool(user.google_sheet_id)
        status = UserStatus(
            has_api_key=has_api_key,
            has_table=has_table
        )
        
        # Красивое приветствие
        welcome_text = Messages.welcome_returning_user(user.full_name, status)
        
        await message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(
                has_api_key=has_api_key,
                has_table=has_table
            )
        )
        return
    
    # Проверяем текущее состояние
    current_state = await state.get_state()
    
    if current_state:
        # Пользователь в процессе регистрации
        logger.info(f"User {telegram_id} in registration state={current_state}")
        
        if current_state == RegistrationStates.GET_NAME.state:
            await message.answer(
                Messages.registration_step_name(1),
                parse_mode="HTML"
            )
        elif current_state == RegistrationStates.GET_EMAIL.state:
            data = await state.get_data()
            name = data.get('name', 'друг')
            await message.answer(
                Messages.registration_step_email(name, 2),
                parse_mode="HTML"
            )
        elif current_state == RegistrationStates.GET_PHONE.state:
            from app.bot.keyboards.reply import get_phone_keyboard
            await message.answer(
                Messages.registration_step_phone(3),
                parse_mode="HTML",
                reply_markup=get_phone_keyboard()
            )
        return
    
    # Новый пользователь - начинаем регистрацию
    await state.set_state(RegistrationStates.GET_NAME)
    
    await message.answer(
        Messages.welcome_new_user(),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help."""
    await message.answer(
        Messages.help_message(),
        parse_mode="HTML"
    )
