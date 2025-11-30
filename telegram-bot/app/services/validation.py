"""Валидация пользовательских данных."""
import re
from typing import Optional


def validate_email(email: str) -> bool:
    """
    Валидация email адреса.
    
    Args:
        email: Email для проверки
        
    Returns:
        True если email валидный, False иначе
    """
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))


def validate_name(name: str) -> bool:
    """
    Валидация имени пользователя.
    
    Args:
        name: Имя для проверки
        
    Returns:
        True если имя валидное, False иначе
    """
    # Удаляем пробелы по краям
    name = name.strip()
    
    # Проверяем длину (от 2 до 50 символов)
    if len(name) < 2 or len(name) > 50:
        return False
    
    return True


def validate_phone(phone: str) -> Optional[str]:
    """
    Валидация номера телефона.
    
    Извлекает цифры из строки и проверяет их количество.
    
    Args:
        phone: Номер телефона для проверки
        
    Returns:
        Очищенный номер телефона или None если невалидный
    """
    # Извлекаем только цифры
    digits = re.sub(r'\D', '', phone)
    
    # Проверяем длину (от 10 до 15 цифр)
    if 10 <= len(digits) <= 15:
        return digits
    
    return None
