"""Обработчики для работы с WB API ключом и генерацией таблиц."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import ApiKeyStates, GoogleSheetStates
from app.bot.keyboards.inline import get_main_menu_keyboard, get_back_keyboard
from app.bot.utils.messages import Messages
from app.database.crud import get_user_by_telegram_id, update_user_api_key
from app.services.wb_integration import wb_integration
from app.utils.logger import logger

router = Router()


@router.callback_query(F.data.in_(["add_api_key", "update_api_key"]))
async def callback_add_api_key(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Добавить API ключ' или 'Обновить API ключ'."""
    await state.set_state(ApiKeyStates.WAITING_FOR_API_KEY)
    
    is_update = callback.data == "update_api_key"
    
    await callback.message.answer(
        Messages.api_key_instructions(),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@router.message(ApiKeyStates.WAITING_FOR_API_KEY)
async def process_api_key(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка введенного API ключа."""
    telegram_id = message.from_user.id
    api_key = message.text.strip()
    
    # Базовая валидация формата ключа
    if len(api_key) < 50:
        await message.answer(
            Messages.error_api_key_invalid(),
            parse_mode="HTML"
        )
        return
    
    # Отправляем сообщение о проверке
    checking_msg = await message.answer(
        Messages.api_key_validating(),
        parse_mode="HTML"
    )
    
    try:
        # Валидируем ключ через реальный запрос к WB API
        is_valid = await wb_integration.validate_api_key(api_key)
        
        if not is_valid:
            await checking_msg.edit_text(
                Messages.api_key_error(),
                parse_mode="HTML"
            )
            return
        
        # Сохраняем API ключ в БД
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await checking_msg.edit_text(
                "❌ Пользователь не найден. Начните с /start",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        await update_user_api_key(session, user, api_key)
        
        await checking_msg.edit_text(
            Messages.api_key_success(),
            parse_mode="HTML"
        )
        
        # Очищаем состояние и показываем меню
        await state.clear()
        
        await message.answer(
            "👇 Выберите действие:",
            reply_markup=get_main_menu_keyboard(has_api_key=True)
        )
        
        logger.info(f"API key saved for user {telegram_id}")
        
    except Exception as e:
        logger.error(f"Error processing API key for user {telegram_id}: {e}", exc_info=True)
        await checking_msg.edit_text(
            Messages.error_general(),
            parse_mode="HTML"
        )
        await state.clear()


@router.callback_query(F.data == "generate_table")
async def callback_generate_table(callback: CallbackQuery, session: AsyncSession):
    """Обработка кнопки 'Получить мою таблицу'."""
    telegram_id = callback.from_user.id
    user = await get_user_by_telegram_id(session, telegram_id)
    
    if not user or not user.wb_api_key:
        await callback.answer(
            "❌ Сначала добавьте API ключ Wildberries!",
            show_alert=True
        )
        return
    
    await callback.answer()
    
    # Отправляем сообщение о начале процесса
    process_msg = await callback.message.answer(
        Messages.table_generating(),
        parse_mode="HTML"
    )
    
    try:
        # Генерируем или получаем таблицу
        sheet_url = await wb_integration.generate_or_get_table(
            user=user,
            session=session
        )
        
        if not sheet_url:
            await process_msg.edit_text(
                Messages.table_error(),
                parse_mode="HTML"
            )
            return
        
        # Проверяем, новая это таблица или обновление существующей
        is_new = not user.google_sheet_id or user.google_sheet_id not in sheet_url
        
        await process_msg.edit_text(
            Messages.table_ready(sheet_url, is_new=is_new),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        logger.info(f"Table generated for user {telegram_id}: {sheet_url}")
        
    except Exception as e:
        logger.error(f"Error generating table for user {telegram_id}: {e}", exc_info=True)
        try:
            await process_msg.edit_text(
                Messages.table_error(),
                parse_mode="HTML"
            )
        except Exception as msg_error:
            logger.error(f"Failed to send error message: {msg_error}")
