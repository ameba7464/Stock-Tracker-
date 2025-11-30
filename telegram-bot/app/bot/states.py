"""FSM States для воронки регистрации."""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния процесса регистрации пользователя."""
    
    GET_NAME = State()  # Ожидание ввода имени
    GET_EMAIL = State()  # Ожидание ввода email
    GET_PHONE = State()  # Ожидание ввода телефона
    
    # [БУДУЩЕЕ] Состояние для интеграции платежей
    # PAYMENT_PENDING = State()  # Ожидание оплаты


class ApiKeyStates(StatesGroup):
    """Состояния для работы с API ключом Wildberries."""
    
    WAITING_FOR_API_KEY = State()  # Ожидание ввода WB API ключа


class GoogleSheetStates(StatesGroup):
    """Состояния для настройки Google Sheets."""
    
    WAITING_FOR_SHEET_ID = State()  # Ожидание ввода ID Google Таблицы
