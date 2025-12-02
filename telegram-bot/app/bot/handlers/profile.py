"""Обработчики редактирования профиля пользователя."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import ProfileEditStates
from app.bot.keyboards.inline import get_profile_keyboard, get_cancel_keyboard
from app.bot.utils.messages import Messages, UserProfile
from app.database.crud import (
    get_user_by_telegram_id,
    update_user_name,
    update_user_email,
    update_user_phone,
)
from app.services.validation import validate_email, validate_name, validate_phone
from app.utils.logger import logger

router = Router()


# ═══════════════════════════════════════════════════
# РЕДАКТИРОВАНИЕ ИМЕНИ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "edit_name")
async def callback_edit_name(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало редактирования имени."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    await state.set_state(ProfileEditStates.WAITING_FOR_NAME)
    
    await callback.message.edit_text(
        Messages.edit_name_prompt(user.name),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard("settings_profile")
    )
    await callback.answer()


@router.message(ProfileEditStates.WAITING_FOR_NAME)
async def process_new_name(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка нового имени."""
    telegram_id = message.from_user.id
    new_name = message.text.strip()
    
    # Валидация
    if not validate_name(new_name):
        await message.answer(
            Messages.error_invalid_name(),
            parse_mode="HTML"
        )
        return
    
    # Обновляем в БД
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Начните с /start")
        await state.clear()
        return
    
    await update_user_name(session, user, new_name)
    await state.clear()
    
    # Показываем успех и возвращаем в профиль
    await message.answer(
        Messages.edit_success("name", new_name),
        parse_mode="HTML"
    )
    
    # Обновляем данные для отображения профиля
    profile = UserProfile(
        name=new_name,
        email=user.email,
        phone=user.phone
    )
    
    await message.answer(
        Messages.settings_profile(profile),
        parse_mode="HTML",
        reply_markup=get_profile_keyboard()
    )
    
    logger.info(f"User {telegram_id} changed name to: {new_name}")


# ═══════════════════════════════════════════════════
# РЕДАКТИРОВАНИЕ EMAIL
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "edit_email")
async def callback_edit_email(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало редактирования email."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    await state.set_state(ProfileEditStates.WAITING_FOR_EMAIL)
    
    await callback.message.edit_text(
        Messages.edit_email_prompt(user.email),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard("settings_profile")
    )
    await callback.answer()


@router.message(ProfileEditStates.WAITING_FOR_EMAIL)
async def process_new_email(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка нового email."""
    telegram_id = message.from_user.id
    new_email = message.text.strip()
    
    # Валидация
    if not validate_email(new_email):
        await message.answer(
            Messages.error_invalid_email(),
            parse_mode="HTML"
        )
        return
    
    # Обновляем в БД
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Начните с /start")
        await state.clear()
        return
    
    await update_user_email(session, user, new_email)
    await state.clear()
    
    # Показываем успех и возвращаем в профиль
    await message.answer(
        Messages.edit_success("email", new_email),
        parse_mode="HTML"
    )
    
    # Обновляем данные для отображения профиля
    profile = UserProfile(
        name=user.name,
        email=new_email,
        phone=user.phone
    )
    
    await message.answer(
        Messages.settings_profile(profile),
        parse_mode="HTML",
        reply_markup=get_profile_keyboard()
    )
    
    logger.info(f"User {telegram_id} changed email to: {new_email}")


# ═══════════════════════════════════════════════════
# РЕДАКТИРОВАНИЕ ТЕЛЕФОНА
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "edit_phone")
async def callback_edit_phone(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало редактирования телефона."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    await state.set_state(ProfileEditStates.WAITING_FOR_PHONE)
    
    await callback.message.edit_text(
        Messages.edit_phone_prompt(user.phone),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard("settings_profile")
    )
    await callback.answer()


@router.message(ProfileEditStates.WAITING_FOR_PHONE)
async def process_new_phone(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка нового телефона."""
    telegram_id = message.from_user.id
    new_phone = validate_phone(message.text)
    
    # Валидация
    if not new_phone:
        await message.answer(
            Messages.error_invalid_phone(),
            parse_mode="HTML"
        )
        return
    
    # Обновляем в БД
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Начните с /start")
        await state.clear()
        return
    
    await update_user_phone(session, user, new_phone)
    await state.clear()
    
    # Показываем успех и возвращаем в профиль
    await message.answer(
        Messages.edit_success("phone", new_phone),
        parse_mode="HTML"
    )
    
    # Обновляем данные для отображения профиля
    profile = UserProfile(
        name=user.name,
        email=user.email,
        phone=new_phone
    )
    
    await message.answer(
        Messages.settings_profile(profile),
        parse_mode="HTML",
        reply_markup=get_profile_keyboard()
    )
    
    logger.info(f"User {telegram_id} changed phone to: {new_phone}")


# ═══════════════════════════════════════════════════
# ОТМЕНА РЕДАКТИРОВАНИЯ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "settings_profile", ProfileEditStates.WAITING_FOR_NAME)
@router.callback_query(F.data == "settings_profile", ProfileEditStates.WAITING_FOR_EMAIL)
@router.callback_query(F.data == "settings_profile", ProfileEditStates.WAITING_FOR_PHONE)
async def callback_cancel_edit_profile(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Отмена редактирования и возврат в профиль."""
    await state.clear()
    
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    profile = UserProfile(
        name=user.name,
        email=user.email,
        phone=user.phone
    )
    
    await callback.message.edit_text(
        Messages.settings_profile(profile),
        parse_mode="HTML",
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()
