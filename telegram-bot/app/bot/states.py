"""FSM States для воронки регистрации и настроек."""
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


class ProfileEditStates(StatesGroup):
    """Состояния редактирования профиля пользователя."""
    
    WAITING_FOR_NAME = State()   # Ожидание нового имени
    WAITING_FOR_EMAIL = State()  # Ожидание нового email
    WAITING_FOR_PHONE = State()  # Ожидание нового телефона
