"""
Custom exceptions for MultiTransfer Bot
"""


class MultiTransferBotError(Exception):
    """Базовое исключение для бота"""
    pass


class PaymentError(MultiTransferBotError):
    """Ошибки связанные с платежами"""
    pass


class AutomationError(MultiTransferBotError):
    """Ошибки браузерной автоматизации"""
    pass


class ProxyError(MultiTransferBotError):
    """Ошибки прокси-серверов"""
    pass


class ValidationError(MultiTransferBotError):
    """Ошибки валидации данных"""
    pass


class DatabaseError(MultiTransferBotError):
    """Ошибки базы данных"""
    pass


class ConfigurationError(MultiTransferBotError):
    """Ошибки конфигурации"""
    pass


class CaptchaError(MultiTransferBotError):
    """Ошибки решения капчи"""
    pass


class BrowserError(AutomationError):
    """Ошибки браузера"""
    pass


class WebDriverError(AutomationError):
    """Ошибки WebDriver"""
    pass


class ElementNotFoundError(AutomationError):
    """Элемент не найден на странице"""
    pass


class TimeoutError(AutomationError):
    """Превышено время ожидания"""
    pass


class NetworkError(MultiTransferBotError):
    """Сетевые ошибки"""
    pass


class RateLimitError(MultiTransferBotError):
    """Превышен лимит запросов"""
    pass


class UserNotFoundError(DatabaseError):
    """Пользователь не найден"""
    pass


class RequisitesNotFoundError(DatabaseError):
    """Реквизиты пользователя не найдены"""
    pass


class PassportDataNotFoundError(DatabaseError):
    """Паспортные данные не найдены"""
    pass