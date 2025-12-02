"""Обработчики главного меню и настроек."""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud import get_user_by_telegram_id
from app.bot.keyboards.inline import (
    get_main_menu_keyboard, 
    get_back_keyboard, 
    get_settings_keyboard,
    get_profile_keyboard,
    get_api_menu_keyboard,
)
from app.bot.utils.messages import Messages, UserStatus, UserProfile
from app.config import settings
from app.utils.logger import logger

router = Router()


# ═══════════════════════════════════════════════════
# ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, session: AsyncSession):
    """Возврат в главное меню."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    has_api_key = bool(user and user.wb_api_key)
    has_table = bool(user and user.google_sheet_id)
    
    # Создаем статус пользователя
    status = UserStatus(
        has_api_key=has_api_key,
        has_table=has_table,
        last_update=user.updated_at if user else None
    )
    
    name = user.name if user else "друг"
    
    # Используем компактное меню
    await callback.message.edit_text(
        Messages.main_menu(name, status),
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(has_api_key=has_api_key, has_table=has_table)
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def callback_about(callback: CallbackQuery):
    """Обработка нажатия на кнопку 'О сервисе'."""
    await callback.message.edit_text(
        Messages.about(),
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Обработка нажатия на кнопку 'Помощь'."""
    await callback.message.edit_text(
        Messages.help_message(),
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


# ═══════════════════════════════════════════════════
# НАСТРОЙКИ (2 уровень)
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "settings")
async def callback_settings(callback: CallbackQuery):
    """Меню настроек."""
    await callback.message.edit_text(
        Messages.settings_menu(),
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_settings")
async def callback_back_to_settings(callback: CallbackQuery):
    """Возврат в меню настроек."""
    await callback.message.edit_text(
        Messages.settings_menu(),
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()


# ═══════════════════════════════════════════════════
# ПРОФИЛЬ (3 уровень)
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "settings_profile")
async def callback_settings_profile(callback: CallbackQuery, session: AsyncSession):
    """Меню профиля пользователя."""
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


# ═══════════════════════════════════════════════════
# API КЛЮЧ (3 уровень)
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "settings_api")
async def callback_settings_api(callback: CallbackQuery, session: AsyncSession):
    """Меню управления API ключом."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    has_api_key = bool(user and user.wb_api_key)
    added_date = user.updated_at if user and user.wb_api_key else None
    
    await callback.message.edit_text(
        Messages.settings_api(has_api_key, added_date),
        parse_mode="HTML",
        reply_markup=get_api_menu_keyboard(has_api_key=has_api_key)
    )
    await callback.answer()


# ═══════════════════════════════════════════════════
# УСТАРЕВШИЕ (для обратной совместимости)
# ═══════════════════════════════════════════════════

@router.callback_query(F.data == "get_sheet")
async def callback_get_sheet(callback: CallbackQuery, session: AsyncSession):
    """Обработка нажатия на кнопку 'Получить таблицу снова'."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user or user.payment_status != 'completed':
        await callback.answer("❌ Вы еще не зарегистрированы!", show_alert=True)
        return
    
    await callback.message.answer(
        "📊 <b>Ваша таблица с материалами:</b>\n\n"
        f"{settings.google_sheet_url}\n\n"
        "Изучайте материалы и развивайте свой бизнес! 🚀",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "refresh_data")
async def callback_refresh_data(callback: CallbackQuery, session: AsyncSession):
    """Обновление данных в таблице (устаревшее)."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user or not user.wb_api_key:
        await callback.answer("❌ Сначала добавьте API ключ!", show_alert=True)
        return
    
    if not user.google_sheet_id:
        await callback.answer("❌ Сначала создайте таблицу!", show_alert=True)
        return
    
    await callback.answer("🔄 Обновляю данные...")
    
    await callback.message.edit_text(
        "🔄 <b>Обновление данных</b>\n\n"
        "Данные в таблице обновляются автоматически каждые 24 часа.\n"
        "Для ручного обновления функция будет добавлена в следующей версии.",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
