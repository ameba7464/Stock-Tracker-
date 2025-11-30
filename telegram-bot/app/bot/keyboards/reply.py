"""Reply клавиатуры для бота."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура для запроса номера телефона.
    
    Returns:
        ReplyKeyboardMarkup с кнопкой отправки контакта
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Нажмите кнопку или введите номер"
    )
    return keyboard


def remove_keyboard() -> ReplyKeyboardRemove:
    """
    Убрать клавиатуру.
    
    Returns:
        ReplyKeyboardRemove
    """
    return ReplyKeyboardRemove()
