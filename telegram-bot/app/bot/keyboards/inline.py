"""Inline клавиатуры для бота с улучшенным UI."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard(has_api_key: bool = False, has_table: bool = False) -> InlineKeyboardMarkup:
    """
    Главное меню с визуальной иерархией кнопок.
    
    Структура:
    - PRIMARY: Главное действие (полная ширина)
    - SECONDARY: Настройки и поддержка (2 в ряд)
    - TERTIARY: О сервисе (полная ширина)
    
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
                    text="📊 Моя таблица",
                    callback_data="generate_table"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="📊 Создать таблицу",
                    callback_data="generate_table"
                )
            )
    else:
        # Пользователь без API ключа — показываем CTA
        builder.row(
            InlineKeyboardButton(
                text="🔑 Подключить WB",
                callback_data="add_api_key"
            )
        )
    
    # ═══════════════════════════════════════════════════
    # LEVEL 2: SECONDARY ACTIONS (2 в ряд)
    # ═══════════════════════════════════════════════════
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
        InlineKeyboardButton(text="💬 Поддержка", callback_data="help"),
    )
    
    # ═══════════════════════════════════════════════════
    # LEVEL 3: TERTIARY (полная ширина)
    # ═══════════════════════════════════════════════════
    builder.row(
        InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about"),
    )
    
    return builder.as_markup()


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Меню настроек (2 уровень).
    
    Returns:
        InlineKeyboardMarkup с настройками
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="settings_profile")
    )
    builder.row(
        InlineKeyboardButton(text="🔑 API ключ", callback_data="settings_api")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu"),
    )
    
    return builder.as_markup()


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Меню редактирования профиля (3 уровень).
    
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Имя", callback_data="edit_name"),
        InlineKeyboardButton(text="📧 Email", callback_data="edit_email"),
        InlineKeyboardButton(text="📱 Тел.", callback_data="edit_phone"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")
    )
    
    return builder.as_markup()


def get_api_menu_keyboard(has_api_key: bool = False) -> InlineKeyboardMarkup:
    """
    Меню управления API ключом (3 уровень).
    
    Args:
        has_api_key: Есть ли API ключ
    
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    if has_api_key:
        builder.row(
            InlineKeyboardButton(text="🔍 Проверить статус", callback_data="api_check_status")
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Обновить", callback_data="api_update"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data="api_delete"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔑 Добавить ключ", callback_data="api_update")
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")
    )
    
    return builder.as_markup()


def get_api_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления API ключа.
    
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data="api_delete_confirm")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="settings_api")
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


def get_cancel_keyboard(callback_data: str = "back_to_settings") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой 'Отмена' для FSM состояний.
    
    Args:
        callback_data: Куда вернуться при отмене
        
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=callback_data)
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
    Меню управления API ключом (устаревшее, для обратной совместимости).
    
    Returns:
        InlineKeyboardMarkup
    """
    return get_api_menu_keyboard(has_api_key=True)
