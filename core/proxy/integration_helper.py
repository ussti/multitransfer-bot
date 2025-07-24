"""
Integration Helper for Smart Proxy Rotation
Помощник интеграции умной ротации прокси в существующий код
"""

import logging
from typing import Optional, Dict, Any
from .smart_rotation_manager import EnhancedProxyManager, CaptchaType

logger = logging.getLogger(__name__)

class ProxyIntegrationHelper:
    """Помощник для интеграции умной ротации прокси"""
    
    @staticmethod
    def detect_captcha_type(page_source: str, current_url: str) -> CaptchaType:
        """
        Определить тип капчи на странице
        
        Args:
            page_source: HTML исходный код страницы
            current_url: Текущий URL
            
        Returns:
            Тип обнаруженной капчи
        """
        page_lower = page_source.lower()
        url_lower = current_url.lower()
        
        # Поиск различных типов капчи
        if 'recaptcha' in page_lower or 'g-recaptcha' in page_lower:
            return CaptchaType.RECAPTCHA
        
        if 'puzzle' in page_lower or 'jigsaw' in page_lower:
            return CaptchaType.PUZZLE
        
        if any(keyword in page_lower for keyword in [
            'captcha', 'verification', 'проверка', 'код подтверждения'
        ]):
            if any(complex_keyword in page_lower for complex_keyword in [
                'slider', 'drag', 'rotate', 'select all', 'выберите все'
            ]):
                return CaptchaType.COMPLEX
            else:
                return CaptchaType.SIMPLE
        
        # Проверка по URL
        if 'captcha' in url_lower or 'verification' in url_lower:
            return CaptchaType.SIMPLE
        
        return CaptchaType.NONE
    
    @staticmethod
    def create_session_context(user_data: Dict[str, Any], 
                             payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать контекст сессии для умного выбора прокси
        
        Args:
            user_data: Данные пользователя
            payment_data: Данные платежа
            
        Returns:
            Контекст для выбора прокси
        """
        context = {
            'user_id': user_data.get('id'),
            'target_country': payment_data.get('recipient_country', 'tj'),  # Таджикистан по умолчанию
            'amount': payment_data.get('amount', 0),
            'currency': payment_data.get('currency', 'TJS'),
            'session_time': payment_data.get('created_at'),
            'user_success_history': user_data.get('successful_payments', 0),
            'is_high_amount': payment_data.get('amount', 0) > 50000,  # Высокая сумма
            'time_of_day': 'day' if 6 <= payment_data.get('hour', 12) <= 18 else 'night'
        }
        
        return context
    
    @staticmethod
    def should_retry_with_new_proxy(error_message: str, attempt_count: int) -> bool:
        """
        Определить, стоит ли повторить попытку с новым прокси
        
        Args:
            error_message: Сообщение об ошибке
            attempt_count: Номер попытки
            
        Returns:
            True если стоит повторить с новым прокси
        """
        if attempt_count >= 3:  # Максимум 3 попытки
            return False
        
        # Ошибки, которые указывают на проблемы с прокси
        proxy_related_errors = [
            'timeout', 'connection', 'proxy', 'network',
            'access denied', 'forbidden', 'blocked',
            'таймаут', 'соединение', 'заблокирован'
        ]
        
        error_lower = error_message.lower()
        return any(error_keyword in error_lower for error_keyword in proxy_related_errors)
    
    @staticmethod
    def extract_performance_metrics(automation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлечь метрики производительности из результата автоматизации
        
        Args:
            automation_result: Результат выполнения автоматизации
            
        Returns:
            Словарь с метриками
        """
        return {
            'session_duration': automation_result.get('total_time', 0),
            'steps_completed': automation_result.get('steps_completed', 0),
            'captcha_solved_time': automation_result.get('captcha_time', 0),
            'page_load_time': automation_result.get('page_load_time', 0),
            'form_filling_time': automation_result.get('form_time', 0),
            'user_agent': automation_result.get('user_agent', ''),
            'browser_version': automation_result.get('browser_version', '')
        }


def create_enhanced_proxy_manager(config: Dict[str, Any]) -> EnhancedProxyManager:
    """
    Фабрика для создания усовершенствованного менеджера прокси
    
    Args:
        config: Конфигурация системы
        
    Returns:
        Настроенный EnhancedProxyManager
    """
    logger.info("🚀 Creating enhanced proxy manager with smart rotation")
    return EnhancedProxyManager(config)


# Пример использования в существующем коде

class ProxyAwareMultiTransferAutomation:
    """
    Обертка для MultiTransferAutomation с поддержкой умной ротации прокси
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.proxy_manager = create_enhanced_proxy_manager(config)
        self.helper = ProxyIntegrationHelper()
        
    async def create_transfer_with_smart_proxy(self, transfer_data: Dict[str, Any], 
                                             user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать перевод с использованием умной ротации прокси
        
        Args:
            transfer_data: Данные перевода
            user_data: Данные пользователя
            
        Returns:
            Результат создания перевода
        """
        from web.browser.multitransfer import MultiTransferAutomation
        
        # Инициализируем менеджер прокси
        await self.proxy_manager.initialize()
        
        # Создаем контекст для выбора прокси
        context = self.helper.create_session_context(user_data, transfer_data)
        
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            
            try:
                # Получаем оптимальный прокси
                proxy = await self.proxy_manager.get_optimal_proxy(context)
                
                logger.info(f"🎯 Attempt {attempt}/{max_attempts} with proxy: "
                           f"{proxy['ip'] if proxy else 'direct connection'}")
                
                # Создаем автоматизацию с выбранным прокси
                automation = MultiTransferAutomation(proxy=proxy, config=self.config)
                
                # Засекаем время начала
                start_time = time.time()
                
                # Выполняем создание перевода
                result = await automation.create_transfer(
                    amount=transfer_data['amount'],
                    recipient_card=transfer_data['recipient_card'],
                    passport_data=transfer_data['passport_data'],
                    recipient_data=transfer_data['recipient_data'],
                    country=transfer_data.get('country', 'tajikistan')
                )
                
                # Определяем тип капчи
                captcha_type = CaptchaType.NONE
                if result.get('captcha_encountered'):
                    if result.get('captcha_type'):
                        captcha_type = CaptchaType(result['captcha_type'])
                    else:
                        # Попытаемся определить по контексту
                        captcha_type = CaptchaType.PUZZLE if result.get('captcha_complex') else CaptchaType.SIMPLE
                
                # Записываем результат в умную ротацию
                if proxy:
                    await self.proxy_manager.record_result(
                        proxy=proxy,
                        success=result.get('success', False),
                        captcha_encountered=result.get('captcha_encountered', False),
                        captcha_type=captcha_type.value,
                        response_time=time.time() - start_time
                    )
                
                # Если успешно - возвращаем результат
                if result.get('success'):
                    logger.info(f"✅ Transfer created successfully on attempt {attempt}")
                    return result
                
                # Если неуспешно, проверяем стоит ли повторить
                error_msg = result.get('error', 'Unknown error')
                if not self.helper.should_retry_with_new_proxy(error_msg, attempt):
                    logger.warning(f"❌ Not retrying - error not proxy-related: {error_msg}")
                    return result
                
                logger.warning(f"⚠️ Attempt {attempt} failed, trying with different proxy: {error_msg}")
                
            except Exception as e:
                logger.error(f"❌ Attempt {attempt} failed with exception: {e}")
                
                # Записываем неудачу, если был прокси
                if 'proxy' in locals() and proxy:
                    await self.proxy_manager.record_result(
                        proxy=proxy,
                        success=False,
                        captcha_encountered=False,
                        captcha_type=CaptchaType.NONE.value,
                        response_time=time.time() - start_time if 'start_time' in locals() else 0
                    )
                
                # Если это последняя попытка, пробрасываем исключение
                if attempt >= max_attempts:
                    raise
        
        # Если все попытки исчерпаны
        return {
            'success': False,
            'error': f'All {max_attempts} attempts failed',
            'attempts_made': max_attempts
        }
    
    def get_proxy_analytics(self) -> Dict[str, Any]:
        """Получить аналитику по прокси"""
        return self.proxy_manager.get_analytics()


# Дополнительные утилиты для интеграции

def patch_existing_payment_service():
    """
    Патч для существующего PaymentService для поддержки умной ротации
    """
    logger.info("🔧 Applying smart proxy rotation patch to PaymentService")
    
    # Этот код можно использовать для обновления существующего сервиса
    # без полной переписи
    
    import types
    from core.services.payment_service import PaymentService
    
    async def enhanced_create_payment(self, user_id: int, amount: float, 
                                    recipient_card: str, country: str = "tajikistan") -> Dict[str, Any]:
        """Расширенный метод создания платежа с умной ротацией"""
        
        # Создаем умную автоматизацию вместо обычной
        smart_automation = ProxyAwareMultiTransferAutomation(self.config.to_dict())
        
        # Получаем данные пользователя
        user = await self.user_repo.get_user(user_id)
        
        # Подготавливаем данные для автоматизации
        transfer_data = {
            'amount': amount,
            'recipient_card': recipient_card,
            'country': country,
            'created_at': datetime.utcnow(),
            'hour': datetime.utcnow().hour
        }
        
        user_data = {
            'id': user_id,
            'successful_payments': user.successful_payments if user else 0
        }
        
        # Выполняем с умной ротацией
        result = await smart_automation.create_transfer_with_smart_proxy(transfer_data, user_data)
        
        return result
    
    # Добавляем новый метод в класс
    PaymentService.create_payment_with_smart_proxy = enhanced_create_payment
    
    logger.info("✅ Smart proxy rotation patch applied successfully")


import time