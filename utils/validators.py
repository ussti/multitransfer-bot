"""
Validation functions for MultiTransfer Bot
"""

import re
from typing import Any, Optional


def validate_amount(amount: Any) -> bool:
    """
    Валидация суммы платежа
    
    Args:
        amount: Сумма для валидации
        
    Returns:
        True если сумма валидна
    """
    try:
        amount_float = float(amount)
        
        # Проверяем границы
        if amount_float < 300:
            return False
        if amount_float > 120000:
            return False
        
        # Проверяем что не отрицательная
        if amount_float <= 0:
            return False
            
        return True
        
    except (ValueError, TypeError):
        return False


def validate_card_number(card_number: str) -> bool:
    """
    Валидация номера банковской карты
    
    Args:
        card_number: Номер карты для валидации
        
    Returns:
        True если номер карты валиден
    """
    if not card_number:
        return False
    
    # Убираем пробелы и дефисы
    clean_number = re.sub(r'[\s\-]', '', card_number)
    
    # Проверяем что только цифры
    if not clean_number.isdigit():
        return False
    
    # Проверяем длину (обычно 13-19 цифр)
    if len(clean_number) < 13 or len(clean_number) > 19:
        return False
    
    # Простая проверка алгоритмом Луна
    return _luhn_check(clean_number)


def _luhn_check(card_number: str) -> bool:
    """
    Проверка номера карты алгоритмом Луна
    
    Args:
        card_number: Номер карты (только цифры)
        
    Returns:
        True если номер проходит проверку Луна
    """
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d*2))
    
    return checksum % 10 == 0


def validate_phone_number(phone: str) -> bool:
    """
    Валидация номера телефона
    
    Args:
        phone: Номер телефона
        
    Returns:
        True если номер валиден
    """
    if not phone:
        return False
    
    # Убираем все кроме цифр
    clean_phone = re.sub(r'[^\d]', '', phone)
    
    # Проверяем длину (российские номера)
    if len(clean_phone) == 11 and clean_phone.startswith('7'):
        return True
    if len(clean_phone) == 10 and clean_phone.startswith('9'):
        return True
    
    return False


def validate_passport_series(series: str) -> bool:
    """
    Валидация серии паспорта РФ
    
    Args:
        series: Серия паспорта
        
    Returns:
        True если серия валидна
    """
    if not series:
        return False
    
    # Убираем пробелы
    clean_series = series.replace(' ', '')
    
    # Проверяем что 4 цифры
    return len(clean_series) == 4 and clean_series.isdigit()


def validate_passport_number(number: str) -> bool:
    """
    Валидация номера паспорта РФ
    
    Args:
        number: Номер паспорта
        
    Returns:
        True если номер валиден
    """
    if not number:
        return False
    
    # Убираем пробелы
    clean_number = number.replace(' ', '')
    
    # Проверяем что 6 цифр
    return len(clean_number) == 6 and clean_number.isdigit()


def validate_date_format(date_str: str) -> bool:
    """
    Валидация формата даты ДД.ММ.ГГГГ
    
    Args:
        date_str: Дата в строковом формате
        
    Returns:
        True если формат корректен
    """
    if not date_str:
        return False
    
    # Проверяем формат ДД.ММ.ГГГГ
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        day, month, year = map(int, date_str.split('.'))
        
        # Базовые проверки
        if not (1 <= day <= 31):
            return False
        if not (1 <= month <= 12):
            return False
        if not (1900 <= year <= 2100):
            return False
        
        return True
        
    except (ValueError, IndexError):
        return False


def validate_country(country: str) -> bool:
    """
    Валидация страны назначения
    
    Args:
        country: Название страны
        
    Returns:
        True если страна поддерживается
    """
    supported_countries = ['tajikistan', 'georgia', 'kyrgyzstan']
    return country.lower() in supported_countries


def validate_bank(bank: str) -> bool:
    """
    Валидация банка
    
    Args:
        bank: Название банка
        
    Returns:
        True если банк поддерживается
    """
    supported_banks = ['korti_milli', 'azizi_molia', 'bank_arvand', 'eskhata_bank']
    return bank.lower() in supported_banks


def validate_currency(currency: str) -> bool:
    """
    Валидация валюты
    
    Args:
        currency: Код валюты
        
    Returns:
        True если валюта поддерживается
    """
    supported_currencies = ['RUB', 'USD', 'EUR', 'TJS', 'KGS', 'GEL']
    return currency.upper() in supported_currencies