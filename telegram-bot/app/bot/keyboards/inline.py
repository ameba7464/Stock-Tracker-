"""Inline клавиатуры для бота с улучшенным UI."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard(has_api_key: bool = False, has_table: bool = False) -> InlineKeyboardMarkup:
    """
    Главное меню с визуальной иерархией кнопок.
    
    Структура:
    - PRIMARY: Главное действие (полная ширина)
    - SECONDARY: Действия (2 в ряд)  
    - TERTIARY: Инфо/Помощь (2 в ряд)
    
    Args:
        has_api_key: Есть ли у пользователя сохраненный API ключ
        has_table: Есть ли уже созданная таблица
    
    Returns:
        InlineKeyboardMarkup с кнопками меню
    """
    builder = InlineKeyboardBuilder()
    
    # ═══════════════════════════════════════════════════
    # LEVEL 1: PRIMARY ACTION (полная ширина)
    # ═══════════════════════════════════════════════════
    if has_api_key:
        if has_table:
            builder.row(
                InlineKeyboardButton(
                    text="📊  Открыть мою таблицу",
                    callback_data="generate_table"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="📊  Создать таблицу",
                    callback_data="generate_table"
                )
            )
        
        # ═══════════════════════════════════════════════════
        # LEVEL 2: SECONDARY ACTIONS (2 в ряд)
        # ═══════════════════════════════════════════════════
        builder.row(
            InlineKeyboardButton(text="🔄 Обновить данные", callback_data="refresh_data"),
            InlineKeyboardButton(text="🔑 API ключ", callback_data="update_api_key"),
        )
    else:
        # Пользователь без API ключа — показываем CTA
        builder.row(
            InlineKeyboardButton(
                text="🚀  Подключить Wildberries",
                callback_data="add_api_key"
            )
        )
    
    # ═══════════════════════════════════════════════════
    # LEVEL 3: INFO & HELP (2 в ряд)
    # ═══════════════════════════════════════════════════
    builder.row(
        InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about"),
        InlineKeyboardButton(text="💬 Поддержка", callback_data="help"),
    )
    
    return builder.as_markup()


def get_settings_keyboard(has_api_key: bool = False) -> InlineKeyboardMarkup:
    """
    Меню настроек.
    
    Args:
        has_api_key: Есть ли API ключ
        
    Returns:
        InlineKeyboardMarkup с настройками
    """
    builder = InlineKeyboardBuilder()
    
    # API ключ
    api_status = " ✓" if has_api_key else ""
    builder.row(
        InlineKeyboardButton(
            text=f"🔑 API ключ{api_status}",
            callback_data="settings_api"
        )
    )
    
    # Уведомления и расписание
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notify"),
        InlineKeyboardButton(text="⏰ Расписание", callback_data="settings_schedule"),
    )
    
    # Назад
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"),
    )
    
    return builder.as_markup()


def get_back_keyboard(callback_data: str = "back_to_menu") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой 'Назад'.
    
    Args:
        callback_data: Куда вернуться
        
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)
    )
    return builder.as_markup()


def get_confirmation_keyboard(
    confirm_callback: str,
    cancel_callback: str = "cancel"
) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действия.
    
    Args:
        confirm_callback: callback для подтверждения
        cancel_callback: callback для отмены
        
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да, подтверждаю", callback_data=confirm_callback)
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback)
    )
    
    return builder.as_markup()


def get_api_key_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Меню управления API ключом.
    
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить ключ", callback_data="update_api_key")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить ключ", callback_data="delete_api_key")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
    )
    
    return builder.as_markup()
