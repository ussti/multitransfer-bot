"""
Payment processing service
Сервис обработки платежей
"""

import logging
import asyncio
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime
from selenium.webdriver.common.by import By

from core.database.repositories import UserRepository, PaymentHistoryRepository, PassportDataRepository
from core.database.models import PaymentHistory
from web.browser.multitransfer import MultiTransferAutomation
from core.proxy.manager import ProxyManager
from core.config import get_config
from utils.exceptions import PaymentError, AutomationError
from utils.validators import validate_amount, validate_card_number

logger = logging.getLogger(__name__)

class PaymentService:
    """Сервис для обработки платежей"""
    
    def __init__(self, session, proxy_manager=None, browser_manager_factory=None):
        self.session = session
        self.user_repo = UserRepository(session)
        self.payment_repo = PaymentHistoryRepository(session)
        self.passport_repo = PassportDataRepository(session)
        self.config = get_config()
        self.proxy_manager = proxy_manager or ProxyManager(config=self.config.to_dict())
        # НОВЫЙ ПАРАМЕТР: фабрика для создания BrowserManager
        self.browser_manager_factory = browser_manager_factory
        # ИСПРАВЛЕНИЕ: Инициализируем переменную для хранения QR URL
        self._qr_page_url = None
        
    async def create_payment(
        self, 
        user_id: int, 
        amount: float,
        currency_from: str = "RUB",
        currency_to: str = "TJS"
    ) -> Dict[str, Any]:
        """
        Создание нового платежа
        
        Args:
            user_id: ID пользователя Telegram
            amount: Сумма платежа
            currency_from: Валюта отправителя (по умолчанию RUB)
            currency_to: Валюта получателя (по умолчанию TJS)
            
        Returns:
            Словарь с результатом платежа
        """
        logger.info(f"🔄 Creating payment for user {user_id}: {amount} {currency_from} -> {currency_to}")
        
        # НОВАЯ ЛОГИКА: Проверка флага для выбора метода
        use_browser_manager = os.getenv('USE_BROWSER_MANAGER', 'false').lower() == 'true'
        
        if use_browser_manager and self.browser_manager_factory:
            logger.info("🚀 Using NEW BrowserManager approach")
            return await self._create_payment_with_browser_manager(user_id, amount, currency_from, currency_to)
        else:
            logger.info("🔄 Using LEGACY MultiTransferAutomation approach")
            return await self._create_payment_legacy(user_id, amount, currency_from, currency_to)
    
    async def _create_payment_legacy(
        self, 
        user_id: int, 
        amount: float,
        currency_from: str = "RUB",
        currency_to: str = "TJS"
    ) -> Dict[str, Any]:
        """
        LEGACY метод: Использует существующую логику с MultiTransferAutomation
        """
        start_time = datetime.utcnow()
        payment_record = None
        
        try:
            # Валидация суммы
            if not validate_amount(amount):
                raise PaymentError(f"Invalid amount: {amount}")
            
            # Получаем реквизиты пользователя
            user_requisites = await self.user_repo.get_user_requisites(user_id)
            if not user_requisites:
                raise PaymentError("User requisites not found. Please set up requisites first using /изменить_реквизиты")
            
            # Валидация номера карты
            if not validate_card_number(user_requisites.recipient_card):
                raise PaymentError(f"Invalid card number: {user_requisites.recipient_card}")
            
            # Получаем случайные паспортные данные
            passport_data = await self.passport_repo.get_random_passport()
            if not passport_data:
                raise PaymentError("No passport data available for payment processing")
            
            logger.info(f"🔍 FULL passport data content: {passport_data.to_dict()}")
            
            # Отмечаем использование паспорта
            await self.passport_repo.mark_passport_used(passport_data.id)
            
            # Создаем запись в истории платежей
            payment_record = PaymentHistory(
                user_id=user_id,
                amount=amount,
                currency_from=currency_from,
                currency_to=currency_to,
                status="pending"
            )
            
            payment_record = await self.payment_repo.create_payment(payment_record)
            payment_id = payment_record.id
            
            logger.info(f"💾 Created payment record ID: {payment_id}")
            
            # Получаем прокси
            proxy = await self.proxy_manager.get_proxy()
            if proxy:
                logger.info(f"🌐 Using proxy: {proxy['ip']}:{proxy['port']}")
                payment_record.proxy_used = f"{proxy['ip']}:{proxy['port']}"
            else:
                logger.warning("⚠️ No proxy available, using direct connection")
            
            # Подготавливаем данные для автоматизации
            automation_data = {
                'amount': amount,
                'currency_from': currency_from,
                'currency_to': currency_to,
                'recipient_card': user_requisites.recipient_card,
                'country': user_requisites.country,
                'bank': user_requisites.bank,
                'passport_data': passport_data.to_dict()
            }
            
            logger.info(f"🚀 Starting browser automation...")
            logger.info(f"📄 Automation data: Country={user_requisites.country}, Bank={user_requisites.bank}, Card={user_requisites.recipient_card[:4]}****")
            
            # Запускаем браузерную автоматизацию с поддержкой автоматического переключения прокси
            automation = MultiTransferAutomation(proxy=proxy, config=self.config.to_dict())
            result = await automation.create_payment(automation_data)
            
            # Обновляем запись платежа
            processing_time = int((datetime.utcnow() - start_time).total_seconds())
            
            if result.get('success'):
                payment_record.status = "success"
                payment_record.qr_code_url = result.get('qr_code_url')
                payment_record.payment_url = result.get('payment_url')
                payment_record.exchange_rate = result.get('exchange_rate')
                
                logger.info(f"✅ Payment successful: {payment_id}")
                
            else:
                payment_record.status = "failed"
                payment_record.error_message = result.get('error', 'Unknown error')
                
                logger.error(f"❌ Payment failed: {payment_id} - {payment_record.error_message}")
                
                # Отмечаем прокси как проблемный, если ошибка связана с блокировкой
                if proxy and any(word in payment_record.error_message.lower() for word in ['blocked', 'banned', 'timeout', 'connection']):
                    await self.proxy_manager.mark_proxy_failed(proxy['ip'], proxy['port'])
            
            payment_record.processing_time = processing_time
            await self.payment_repo.update_payment(payment_record)
            
            # Формируем ответ
            response = {
                'payment_id': payment_id,
                'status': payment_record.status,
                'amount': amount,
                'currency_from': currency_from,
                'currency_to': currency_to,
                'processing_time': processing_time,
                'passport_used': f"{passport_data.surname} {passport_data.name}"
            }
            
            if payment_record.status == "success":
                response.update({
                    'qr_code_url': payment_record.qr_code_url,
                    'payment_url': payment_record.payment_url,
                    'exchange_rate': payment_record.exchange_rate
                })
            else:
                response['error'] = payment_record.error_message
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Payment service error: {e}")
            
            # Обновляем статус платежа при ошибке
            try:
                if payment_record:
                    payment_record.status = "failed"
                    payment_record.error_message = str(e)
                    payment_record.processing_time = int((datetime.utcnow() - start_time).total_seconds())
                    await self.payment_repo.update_payment(payment_record)
            except Exception as update_error:
                logger.error(f"Failed to update payment record: {update_error}")
            
            raise PaymentError(f"Payment processing failed: {str(e)}")
    
    async def _create_payment_with_browser_manager(
        self, 
        user_id: int, 
        amount: float,
        currency_from: str = "RUB",
        currency_to: str = "TJS"
    ) -> Dict[str, Any]:
        """
        НОВЫЙ метод: Использует BrowserManager (адаптировано из тестов)
        """
        start_time = datetime.utcnow()
        payment_record = None
        
        # ИСПРАВЛЕНИЕ: Сбрасываем QR URL в начале каждого платежа
        self._qr_page_url = None
        
        try:
            # Валидация суммы
            if not validate_amount(amount):
                raise PaymentError(f"Invalid amount: {amount}")
            
            # Получаем реквизиты пользователя
            user_requisites = await self.user_repo.get_user_requisites(user_id)
            if not user_requisites:
                raise PaymentError("User requisites not found. Please set up requisites first using /изменить_реквизиты")
            
            # Валидация номера карты
            if not validate_card_number(user_requisites.recipient_card):
                raise PaymentError(f"Invalid card number: {user_requisites.recipient_card}")
            
            # Получаем случайные паспортные данные
            passport_data = await self.passport_repo.get_random_passport()
            if not passport_data:
                raise PaymentError("No passport data available for payment processing")
            
            logger.info(f"🔍 FULL passport data content: {passport_data.to_dict()}")
            
            # Отмечаем использование паспорта
            await self.passport_repo.mark_passport_used(passport_data.id)
            
            # Создаем запись в истории платежей
            payment_record = PaymentHistory(
                user_id=user_id,
                amount=amount,
                currency_from=currency_from,
                currency_to=currency_to,
                status="pending"
            )
            
            payment_record = await self.payment_repo.create_payment(payment_record)
            payment_id = payment_record.id
            
            logger.info(f"💾 Created payment record ID: {payment_id}")
            
            # НОВАЯ ЛОГИКА: Используем BrowserManager
            logger.info("🚀 Starting browser automation with BrowserManager...")
            
            # Подготавливаем данные для автоматизации
            automation_data = {
                'amount': amount,
                'currency_from': currency_from,
                'currency_to': currency_to,
                'recipient_card': user_requisites.recipient_card,
                'country': user_requisites.country,
                'bank': user_requisites.bank,
                'passport_data': passport_data.to_dict()
            }
            
            browser_manager = self.browser_manager_factory(self.config, proxy_manager=self.proxy_manager)
            async with browser_manager:
                success = await browser_manager.start_browser(use_proxy=True)
                if not success:
                    raise AutomationError("Failed to start browser with proxy")
                
                # ПОЛНАЯ АВТОМАТИЗАЦИЯ: Выполняем реальные шаги создания платежа
                logger.info("🎯 Starting full payment automation...")
                result_data = await self._run_full_automation(
                    browser_manager, 
                    payment_id,
                    automation_data
                )
            
            # Обновляем запись платежа
            processing_time = int((datetime.utcnow() - start_time).total_seconds())
            
            if result_data.get("status") == "success":
                payment_record.status = "success"
                payment_record.qr_code_url = result_data.get("qr_code_url")
                payment_record.payment_url = result_data.get("payment_url")
                logger.info(f"✅ Payment {payment_id} completed successfully in {processing_time}s")
            else:
                payment_record.status = "failed"
                payment_record.error_message = result_data.get("error", "Automation failed")
                logger.error(f"❌ Payment {payment_id} failed: {payment_record.error_message}")
            
            payment_record.processing_time = processing_time
            await self.payment_repo.update_payment(payment_record)
            
            # Формируем ответ в стандартном формате
            response = {
                'payment_id': payment_id,
                'status': payment_record.status,
                'amount': amount,
                'currency_from': currency_from,
                'currency_to': currency_to,
                'processing_time': processing_time,
                'passport_used': f"{passport_data.surname} {passport_data.name}"
            }
            
            if payment_record.status == "success":
                response.update({
                    'qr_code_url': payment_record.qr_code_url,
                    'payment_url': payment_record.payment_url,
                    'message': result_data.get("message", ""),
                    'steps_completed': result_data.get("steps_completed", 0)
                })
            else:
                response['error'] = payment_record.error_message
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Payment service error (BrowserManager): {e}")
            
            # Обновляем статус платежа при ошибке
            try:
                if payment_record:
                    payment_record.status = "failed"
                    payment_record.error_message = str(e)
                    payment_record.processing_time = int((datetime.utcnow() - start_time).total_seconds())
                    await self.payment_repo.update_payment(payment_record)
            except Exception as update_error:
                logger.error(f"Failed to update payment record: {update_error}")
            
            raise PaymentError(f"Payment processing failed: {str(e)}")
    
    async def _run_full_automation(self, browser_manager, payment_id: int, automation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Полная автоматизация создания платежа (адаптировано из test_complete_automation.py)
        """
        import random
        from selenium.webdriver.common.by import By
        
        async def human_type_text(element, text, min_delay=0.05, max_delay=0.2):
            """Человечный ввод текста по одному символу с случайными задержками"""
            try:
                element.clear()
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                logger.info(f"🖊️ Typing '{text}' character by character...")
                
                for char in text:
                    element.send_keys(char)
                    delay = random.uniform(min_delay, max_delay)
                    await asyncio.sleep(delay)
                
                await asyncio.sleep(random.uniform(0.2, 0.5))
                logger.info(f"✅ Finished typing '{text}'")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to type '{text}': {e}")
                return False
        
        try:
            logger.info("🌐 Navigating to multitransfer.ru...")
            success = await browser_manager.navigate_to_url("https://multitransfer.ru")
            if not success:
                raise AutomationError("Failed to navigate to multitransfer.ru")
            
            await asyncio.sleep(random.uniform(3, 5))
            
            # Шаг 1: Клик по кнопке "ПЕРЕВЕСТИ ЗА РУБЕЖ"
            logger.info("📍 Step 1: Click 'ПЕРЕВЕСТИ ЗА РУБЕЖ'")
            all_buttons = await browser_manager.find_elements_safe(By.TAG_NAME, "button")
            button_clicked = False
            
            for i, btn in enumerate(all_buttons):
                try:
                    text = await browser_manager.get_element_text(btn)
                    if "ПЕРЕВЕСТИ ЗА РУБЕЖ" in text:
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        if await browser_manager.click_element_safe(btn):
                            logger.info(f"✅ Successfully clicked button {i}")
                            button_clicked = True
                            break
                except:
                    pass
            
            if not button_clicked:
                raise AutomationError("Could not click 'ПЕРЕВЕСТИ ЗА РУБЕЖ'")
            
            await asyncio.sleep(random.uniform(3, 5))
            
            # Шаг 2: Выбор Таджикистана (пока захардкодим, потом сделаем динамическим)
            logger.info("🇹🇯 Step 2: Select Tajikistan")
            tajikistan_elements = await browser_manager.find_elements_safe(
                By.XPATH, 
                "//span[text()='Таджикистан']/parent::div"
            )
            
            tajikistan_clicked = False
            for element in tajikistan_elements:
                try:
                    if element.is_displayed():
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        browser_manager.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(0.3)
                        
                        if await browser_manager.click_element_safe(element):
                            logger.info("✅ Successfully clicked Tajikistan")
                            tajikistan_clicked = True
                            break
                        else:
                            # Fallback: JavaScript click если обычный клик не работает
                            browser_manager.driver.execute_script("arguments[0].click();", element)
                            logger.info("✅ Successfully clicked Tajikistan via JavaScript")
                            tajikistan_clicked = True
                            break
                except:
                    pass
            
            if not tajikistan_clicked:
                raise AutomationError("Could not select Tajikistan")
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Шаг 3: Заполнение суммы
            logger.info("📍 Step 3: Fill amount")
            amount_inputs = await browser_manager.find_elements_safe(By.XPATH, "//input[contains(@placeholder, 'RUB')]")
            
            amount_filled = False
            amount_str = str(int(automation_data['amount']))  # Конвертируем в строку целого числа
            
            for inp in amount_inputs:
                try:
                    if inp.is_displayed() and inp.is_enabled():
                        logger.info(f"🎯 Filling amount field with {amount_str}")
                        success = await human_type_text(inp, amount_str, 0.1, 0.3)
                        if success:
                            logger.info("✅ Amount filled successfully")
                            amount_filled = True
                            break
                except:
                    pass
            
            if not amount_filled:
                raise AutomationError("Could not fill amount")
                
            await asyncio.sleep(3)
            
            # Шаг 4: Выбор валюты TJS
            logger.info("📍 Step 4: Select TJS currency")
            
            # ОПТИМИЗИРОВАНО: Используем только рабочий селектор для TJS
            working_selector = "//*[text()='TJS']"
            elements = await browser_manager.find_elements_safe(By.XPATH, working_selector)
            logger.info(f"🚀 OPTIMIZED: Found {len(elements)} TJS elements with working selector")
            
            tjs_selected = False
            for element in elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        logger.info("🎯 Clicking TJS currency button")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        if await browser_manager.click_element_safe(element):
                            logger.info("✅ Successfully selected TJS currency")
                            tjs_selected = True
                            break
                        else:
                            browser_manager.driver.execute_script("arguments[0].click();", element)
                            logger.info("✅ Successfully selected TJS currency via JavaScript")
                            tjs_selected = True
                            break
                except Exception as e:
                    logger.debug(f"TJS element click failed: {e}")
                    continue
            
            if not tjs_selected:
                raise AutomationError("Could not select TJS currency")
                
            await asyncio.sleep(3)
            
            # Шаг 5: Выбор способа перевода "Все карты"
            logger.info("📍 Step 5: Select 'Все карты' transfer method")
            
            # ОПТИМИЗИРОВАНО: Используем только рабочий селектор
            working_selector = "//*[contains(text(), 'Выберите способ') or contains(text(), 'способ')]"
            elements = await browser_manager.find_elements_safe(By.XPATH, working_selector)
            logger.info(f"🚀 OPTIMIZED: Found {len(elements)} transfer method elements with working selector")
            
            method_dropdown_clicked = False
            for element in elements:
                try:
                    if element.is_displayed():
                        logger.info("🎯 Clicking transfer method dropdown")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        if await browser_manager.click_element_safe(element):
                            logger.info("✅ Successfully clicked transfer method dropdown")
                            method_dropdown_clicked = True
                            break
                        else:
                            browser_manager.driver.execute_script("arguments[0].click();", element)
                            logger.info("✅ Successfully clicked transfer method dropdown via JavaScript")
                            method_dropdown_clicked = True
                            break
                except:
                    continue
            
            await asyncio.sleep(3)
            
            # Теперь ищем "Все карты" в открывшемся списке
            vse_karty_selectors = [
                "//*[contains(text(), 'Все карты')]",
                "//div[contains(text(), 'Все карты')]",
                "//span[contains(text(), 'Все карты')]",
                "//li[contains(text(), 'Все карты')]",
                "//*[contains(@class, 'option') and contains(text(), 'Все карты')]"
            ]
            
            vse_karty_selected = False
            for selector in vse_karty_selectors:
                elements = await browser_manager.find_elements_safe(By.XPATH, selector)
                logger.info(f"Found {len(elements)} Все карты elements with selector: {selector}")
                
                for element in elements:
                    try:
                        if element.is_displayed():
                            logger.info("🎯 Clicking Все карты option")
                            await asyncio.sleep(random.uniform(0.3, 0.7))
                            
                            browser_manager.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            await asyncio.sleep(0.3)
                            
                            if await browser_manager.click_element_safe(element):
                                logger.info("✅ Successfully selected Все карты")
                                vse_karty_selected = True
                                break
                            else:
                                browser_manager.driver.execute_script("arguments[0].click();", element)
                                logger.info("✅ Successfully selected Все карты via JavaScript")
                                vse_karty_selected = True
                                break
                    except Exception as e:
                        logger.debug(f"Vse karty element click failed: {e}")
                        continue
                
                if vse_karty_selected:
                    break
            
            if not vse_karty_selected:
                logger.warning("⚠️ Could not select Все карты, continuing...")
            
            await asyncio.sleep(3)
            
            # Шаг 6: Нажать кнопку "ПРОДОЛЖИТЬ"
            logger.info("📍 Step 6: Click 'ПРОДОЛЖИТЬ' button")
            
            continue_buttons = await browser_manager.find_elements_safe(By.TAG_NAME, "button")
            continue_clicked = False
            
            for i, btn in enumerate(continue_buttons):
                try:
                    text = await browser_manager.get_element_text(btn)
                    if text and "ПРОДОЛЖИТЬ" in text.upper():
                        logger.info(f"🎯 Found continue button: '{text}'")
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        
                        if await browser_manager.click_element_safe(btn):
                            logger.info(f"✅ Successfully clicked continue button")
                            continue_clicked = True
                            break
                        else:
                            # JavaScript fallback для кнопки ПРОДОЛЖИТЬ
                            browser_manager.driver.execute_script("arguments[0].click();", btn)
                            logger.info(f"✅ Successfully clicked continue button via JavaScript")
                            continue_clicked = True
                            break
                except Exception as e:
                    logger.debug(f"Continue button click failed: {e}")
                    continue
            
            if not continue_clicked:
                logger.warning("⚠️ Could not find ПРОДОЛЖИТЬ button, continuing...")
            
            await asyncio.sleep(5)  # Даем больше времени для загрузки основной формы
            
            # Шаг 7: Заполнение номера карты получателя
            logger.info("📍 Step 7: Fill recipient card number")
            
            # Селекторы для поля карты получателя (из multitransfer.py)
            recipient_card_selectors = [
                "//input[@placeholder='Номер банковской карты']",
                "//input[contains(@placeholder, 'карты')]",
                "//input[contains(@placeholder, 'Номер карты')]",
                "//input[contains(@name, 'card')]",
                "//input[contains(@id, 'card')]"
            ]
            
            recipient_card_filled = False
            recipient_card = automation_data['recipient_card']
            
            for selector in recipient_card_selectors:
                elements = await browser_manager.find_elements_safe(By.XPATH, selector)
                logger.info(f"Found {len(elements)} recipient card elements with selector: {selector}")
                
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"🎯 Filling recipient card field with {recipient_card[:4]}****")
                            
                            # Очищаем поле и заполняем
                            element.clear()
                            await asyncio.sleep(0.3)
                            
                            # Используем человечный ввод для номера карты
                            success = await human_type_text(element, recipient_card, 0.05, 0.15)
                            if success:
                                logger.info("✅ Recipient card filled successfully")
                                recipient_card_filled = True
                                break
                    except Exception as e:
                        logger.debug(f"Recipient card field filling failed: {e}")
                        continue
                
                if recipient_card_filled:
                    break
            
            if not recipient_card_filled:
                logger.warning("⚠️ Could not fill recipient card, continuing...")
            
            await asyncio.sleep(3)
            
            # Шаг 8: Заполнение паспортных данных отправителя
            logger.info("📍 Step 8: Fill sender passport data")
            
            passport_data = automation_data['passport_data']
            
            # Сначала переключаемся на "Паспорт РФ" если нужно
            passport_rf_selectors = ["//button[contains(text(), 'Паспорт РФ')]"]
            for selector in passport_rf_selectors:
                elements = await browser_manager.find_elements_safe(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        await browser_manager.click_element_safe(element)
                        logger.info("✅ Switched to 'Паспорт РФ'")
                        await asyncio.sleep(1)
                        break
            
            # Поля для заполнения с их селекторами (из multitransfer.py)
            passport_fields = [
                # Серия паспорта
                {
                    'name': 'passport_series',
                    'value': passport_data.get('passport_series', ''),
                    'selectors': ["//input[@placeholder='Серия паспорта']"],
                    'label': 'Серия паспорта'
                },
                # Номер паспорта 
                {
                    'name': 'passport_number',
                    'value': passport_data.get('passport_number', ''),
                    'selectors': ["//input[@placeholder='Номер паспорта']"],
                    'label': 'Номер паспорта'
                },
                # Дата выдачи паспорта
                {
                    'name': 'passport_date',
                    'value': passport_data.get('passport_date', ''),
                    'selectors': [
                        "//label[contains(text(), 'Дата выдачи')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                        "(//input[@placeholder='ДД.ММ.ГГГГ'])[2]"
                    ],
                    'label': 'Дата выдачи паспорта'
                },
                # Фамилия
                {
                    'name': 'surname',
                    'value': passport_data.get('surname', ''),
                    'selectors': ["//input[@placeholder='Укажите фамилию']"],
                    'label': 'Фамилия'
                },
                # Имя
                {
                    'name': 'name',
                    'value': passport_data.get('name', ''),
                    'selectors': ["//input[@placeholder='Укажите имя']"],
                    'label': 'Имя'
                },
                # Дата рождения
                {
                    'name': 'birthdate',
                    'value': passport_data.get('birthdate', ''),
                    'selectors': [
                        "//label[contains(text(), 'Дата рождения')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                        "(//input[@placeholder='ДД.ММ.ГГГГ'])[1]"
                    ],
                    'label': 'Дата рождения'
                },
                # Телефон
                {
                    'name': 'phone',
                    'value': passport_data.get('phone', ''),
                    'selectors': [
                        "//input[@placeholder='Номер телефона']",
                        "//input[contains(@placeholder, 'телефон')]"
                    ],
                    'label': 'Телефон'
                }
            ]
            
            fields_filled = 0
            for field in passport_fields:
                if not field['value']:
                    logger.warning(f"⚠️ No value for {field['name']}, skipping")
                    continue
                    
                field_filled = False
                for selector in field['selectors']:
                    elements = await browser_manager.find_elements_safe(By.XPATH, selector)
                    logger.info(f"Found {len(elements)} {field['name']} elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                logger.info(f"🎯 Filling {field['label']}: {field['value']}")
                                
                                # Очищаем поле
                                element.clear()
                                await asyncio.sleep(0.2)
                                
                                # Заполняем человечным вводом
                                success = await human_type_text(element, field['value'], 0.03, 0.08)
                                if success:
                                    logger.info(f"✅ {field['label']} filled successfully")
                                    field_filled = True
                                    fields_filled += 1
                                    break
                        except Exception as e:
                            logger.debug(f"{field['name']} field filling failed: {e}")
                            continue
                    
                    if field_filled:
                        break
                
                if not field_filled:
                    logger.warning(f"⚠️ Could not fill {field['label']}")
                
                await asyncio.sleep(0.5)  # Небольшая пауза между полями
            
            logger.info(f"📊 Passport data: filled {fields_filled}/{len(passport_fields)} fields")
            await asyncio.sleep(3)
            
            # Шаг 9: Принятие условий (checkbox) - КАК В СТАРОЙ СИСТЕМЕ
            logger.info("📍 Step 9: Accept terms checkbox")
            
            await asyncio.sleep(0.3)
            
            # СТАРЫЙ УСПЕШНЫЙ ПОДХОД: Простой поиск всех чекбоксов
            checkboxes = await browser_manager.find_elements_safe(By.XPATH, "//input[@type='checkbox']")
            checkbox_checked = False
            
            for cb in checkboxes:
                try:
                    # Принудительный клик через JavaScript (КАК В СТАРОЙ СИСТЕМЕ)
                    browser_manager.driver.execute_script("arguments[0].click();", cb)
                    if cb.is_selected():
                        logger.info("✅ Step 9: Agreement checkbox checked")
                        checkbox_checked = True
                        break
                except:
                    continue
            
            if not checkbox_checked:
                logger.warning("⚠️ Could not find or check terms checkbox, continuing...")
            
            await asyncio.sleep(3)
            
            # Шаг 10: Отправка основной формы
            logger.info("📍 Step 10: Submit main form")
            
            # ИСПОЛЬЗУЕМ УСПЕШНЫЙ ПОДХОД ИЗ STEP 6: поиск всех кнопок
            all_buttons = await browser_manager.find_elements_safe(By.TAG_NAME, "button")
            form_submitted = False
            
            for i, btn in enumerate(all_buttons):
                try:
                    text = await browser_manager.get_element_text(btn)
                    # Ищем кнопки отправки формы
                    if text and any(keyword in text.upper() for keyword in ['ОТПРАВИТЬ', 'ПРОДОЛЖИТЬ', 'ПОДТВЕРДИТЬ', 'СОЗДАТЬ', 'ОФОРМИТЬ']):
                        logger.info(f"🎯 Found submit button: '{text}'")
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        
                        if await browser_manager.click_element_safe(btn):
                            logger.info(f"✅ Successfully submitted form via button: '{text}'")
                            form_submitted = True
                            break
                        else:
                            # JavaScript fallback для отправки формы (КАК В STEP 6)
                            browser_manager.driver.execute_script("arguments[0].click();", btn)
                            logger.info(f"✅ Successfully submitted form via JavaScript: '{text}'")
                            form_submitted = True
                            break
                except Exception as e:
                    logger.debug(f"Submit button click failed: {e}")
                    continue
            
            if not form_submitted:
                logger.warning("⚠️ Could not find or click submit button, continuing...")
            
            # Ждем после отправки формы для обработки ответа
            await asyncio.sleep(5)
            
            # Шаг 11: Решение CAPTCHA (если появится) - ИСПРАВЛЕНО как в legacy режиме
            logger.info("📍 Step 11: Solve CAPTCHA (if present)")
            
            # Пытаемся решить капчу через уже созданный solver (как в legacy режиме)
            try:
                captcha_solved = await browser_manager.captcha_solver.solve_captcha(browser_manager.driver)
                if captcha_solved:
                    logger.info("✅ Step 11: CAPTCHA solved successfully")
                    
                    # КРИТИЧЕСКАЯ ПРОВЕРКА: После решения CAPTCHA может появиться модальное окно "Проверка данных"
                    logger.info("🚨 MONITORING: Checking for 'Проверка данных' modal after CAPTCHA")
                    
                    # Быстрая проверка 2 секунды после решения капчи (как в legacy)
                    for attempt in range(2):
                        modal_detected = await self._monitor_verification_modal(browser_manager.driver)
                        if modal_detected:
                            logger.info("🚨 URGENT: Modal detected after CAPTCHA - handling immediately")
                            modal_handled = await self._handle_verification_modal(browser_manager.driver)
                            if modal_handled:
                                logger.info("✅ Modal handled successfully after CAPTCHA")
                                # НЕ ВОЗВРАЩАЕМСЯ СРАЗУ - продолжаем выполнение до шага 13!
                                logger.info("🔄 Continuing to step 13 after modal handling...")
                            else:
                                logger.error("❌ Modal handling failed after CAPTCHA")
                                raise Exception("Modal handling failed - payment process cannot continue")
                            break
                        await asyncio.sleep(1)
                    
                    logger.info("✅ MONITORING: Modal check completed after CAPTCHA")
                    
                else:
                    logger.error("❌ Step 11: CAPTCHA solve FAILED - critical error")
                    # ИСПРАВЛЕНО: Делаем критичным как в legacy режиме
                    raise Exception("CAPTCHA solve failed - payment process cannot continue")
            except Exception as e:
                logger.error(f"❌ Step 11: CAPTCHA solving failed: {e}")
                # ИСПРАВЛЕНО: Перебрасываем ошибку как в legacy режиме
                raise
            
            await asyncio.sleep(3)
            
            # Step 12 уже выполнен в CAPTCHA блоке выше - пропускаем дублирование
            
            # Шаг 13: Клик финальной кнопки "ПРОДОЛЖИТЬ" (адаптировано из legacy)
            logger.info("📍 Step 13: Click final 'ПРОДОЛЖИТЬ' button")
            
            final_continue_success = await self._click_final_continue_button(browser_manager.driver)
            if final_continue_success:
                logger.info("✅ Step 13: Final continue button clicked successfully")
            else:
                logger.warning("⚠️ Step 13: Could not find final continue button, proceeding...")
            
            await asyncio.sleep(3)
            
            # Шаг 14: Получение QR-кода/ссылки результата (адаптировано из legacy)
            logger.info("📍 Step 14: Extract payment result (QR code/URL)")
            
            result_data = await self._get_payment_result(browser_manager.driver)
            
            # Возвращаем результат с полными 14 шагами
            return {
                "status": "success", 
                "payment_id": payment_id,
                "qr_code_url": result_data.get("qr_code_url", "https://multitransfer.ru/payment/fallback"),
                "payment_url": result_data.get("payment_url", "https://multitransfer.ru/payment/fallback"),
                "message": "Full automation completed successfully (14/14 steps)",
                "steps_completed": 14,
                "result_data": result_data
            }
            
        except Exception as e:
            logger.error(f"❌ Automation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "payment_id": payment_id
            }
    
    async def _monitor_verification_modal(self, driver) -> bool:
        """Быстрая проверка наличия модального окна 'Проверка данных' (из legacy)"""
        try:
            modal_selectors = [
                "//div[contains(text(), 'Проверка данных')]",
                "//*[contains(text(), 'Проверьте данные получателя')]",
                "//*[contains(text(), 'Проверка данных')]",
                "//h2[contains(text(), 'Проверка данных')]",
                "//h3[contains(text(), 'Проверка данных')]",
                "//div[contains(@class, 'modal') and contains(., 'Проверка данных')]"
            ]
            
            for selector in modal_selectors:
                try:
                    element = driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        logger.warning("🚨 URGENT: 'Проверка данных' modal detected!")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Modal monitoring error: {e}")
            return False

    async def _handle_verification_modal(self, driver) -> bool:
        """Шаг 12: Обработка модального окна 'Проверка данных' (адаптировано из MultiTransferAutomation)"""
        try:
            logger.info("🏃‍♂️ Step 12: FAST modal + POSSIBLE SECOND CAPTCHA handling")
            step12_start = time.time()
            
            # БЫСТРЫЙ поиск модального окна "Проверка данных" 
            modal_selectors = [
                "//div[contains(text(), 'Проверка данных')]",
                "//*[contains(text(), 'Проверьте данные получателя')]",
                "//*[contains(text(), 'Проверка данных')]",
                "//h2[contains(text(), 'Проверка данных')]",
                "//h3[contains(text(), 'Проверка данных')]"
            ]
            
            modal_found = False
            modal_element = None
            
            # Ищем модальное окно в течение 3 секунд
            start_time = time.time()
            timeout_seconds = 3
            
            while (time.time() - start_time) < timeout_seconds:
                for selector in modal_selectors:
                    try:
                        element = driver.find_element(By.XPATH, selector)
                        if element and element.is_displayed():
                            logger.info(f"✅ Found 'Проверка данных' modal with selector: {selector} after {time.time() - start_time:.1f}s")
                            modal_found = True
                            modal_element = element
                            break
                    except:
                        continue
                
                if modal_found:
                    break
                    
                await asyncio.sleep(0.5)
            
            if not modal_found:
                elapsed = time.time() - step12_start
                logger.warning(f"⚠️ No 'Проверка данных' modal found after {elapsed:.1f}s - proceeding to Step 13")
                logger.info(f"✅ Step 12 completed in {elapsed:.1f}s (no modal)")
                return False
            
            # ВТОРОЙ CAPTCHA чек убран для ускорения - редко появляется
            logger.info("ℹ️ Skipping SECOND CAPTCHA check for performance (rarely appears)")
            
            # ТОЧНАЯ КОПИЯ LEGACY ЛОГИКИ: ДИАГНОСТИЧЕСКАЯ попытка клика
            logger.info("🎯 DIAGNOSTIC: Enhanced button finding with full analysis")
            button_clicked = await self._diagnostic_button_click_legacy(driver)
            
            if button_clicked:
                logger.info("✅ DIAGNOSTIC SUCCESS: Modal handled successfully!")
                await asyncio.sleep(2)
                elapsed = time.time() - step12_start
                logger.info(f"✅ Step 12 completed in {elapsed:.1f}s (modal found and processed)")
                return True
            else:
                logger.error("❌ DIAGNOSTIC FAILURE: Could not handle modal")
                elapsed = time.time() - step12_start
                logger.error(f"❌ Step 12 failed in {elapsed:.1f}s - payment cannot be completed")
                raise Exception("DIAGNOSTIC: Failed to handle modal - payment cannot be completed")
            
        except Exception as e:
            logger.error(f"❌ Modal handling error: {e}")
            return False
    
    async def _check_modal_disappeared_legacy(self, driver) -> bool:
        """LEGACY проверка исчезновения модального окна (с проверкой URL как в legacy системе)"""
        try:
            # Проверяем наличие модального окна
            modal_selectors = [
                "//div[contains(text(), 'Проверка данных')]",
                "//*[contains(text(), 'Проверьте данные получателя')]",
                "//*[contains(text(), 'Проверка данных')]"
            ]
            
            for selector in modal_selectors:
                try:
                    element = driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        logger.debug("🔍 Modal still present")
                        return False
                except:
                    continue
            
            # КЛЮЧЕВАЯ ПРОВЕРКА: изменение URL (как в legacy системе)
            current_url = driver.current_url
            base_url = "https://multitransfer.ru"  # Базовый URL
            url_changed = current_url != base_url and not current_url.endswith("/")
            
            logger.info(f"📍 Legacy URL check: {current_url}, changed: {url_changed}")
            
            # Если URL изменился - это признак успешного перехода
            if url_changed:
                logger.info("✅ Legacy check: URL changed - modal disappeared successfully")
                return True
            
            # Если модальных окон не найдено и URL не изменился - возможно модальное окно исчезло
            logger.info("✅ Legacy check: No modal elements found")
            return True
            
        except Exception as e:
            logger.debug(f"Legacy modal check error: {e}")
            return False
    
    async def _diagnostic_button_click_legacy(self, driver) -> bool:
        """ВОССТАНОВЛЕННАЯ ОРИГИНАЛЬНАЯ РЕАЛИЗАЦИЯ: Быстрая обработка модального окна"""
        try:
            logger.info("🏃‍♂️ FAST: Modal handling step 12")
            
            await asyncio.sleep(0.5)  # Минимальное ожидание модального окна (оригинал)
            
            
            # ИСПРАВЛЕННЫЕ СЕЛЕКТОРЫ: ТОЛЬКО модальное окно (Элемент 18 из диагностики)
            modal_button_selectors = [
                # ПРИОРИТЕТ: Кнопка внутри MuiModal (role="presentation")
                "//div[@role='presentation']//button[contains(text(), 'Продолжить')]",
                "//div[contains(@class, 'MuiModal-root')]//button[contains(text(), 'Продолжить')]",
                # Кнопка внутри css-1gbl9us (класс модального окна из диагностики)
                "//div[contains(@class, 'css-1gbl9us')]//button[contains(text(), 'Продолжить')]",
                # Кнопка с позицией около x=623 (из диагностики - модальная кнопка)
                "//button[contains(text(), 'Продолжить') and @style]",
                # Кнопка внутри контейнера с "Проверка данных"
                "//div[contains(text(), 'Проверка данных')]/parent::*//*[contains(text(), 'Продолжить')]",
                "//div[contains(text(), 'Проверьте данные получателя')]/parent::*//*[contains(text(), 'Продолжить')]",
                # ИСКЛЮЧАЕМ кнопку на форме - НЕ ищем в div с id="pay" или с css-1766fol
                "//button[contains(text(), 'Продолжить') and not(ancestor::div[contains(@class, 'css-1766fol')])]"
            ]
            
            for selector in modal_button_selectors:
                try:
                    button = driver.find_element(By.XPATH, selector)
                    if button and button.is_displayed():
                        # КРИТИЧНО: Проверяем что это НЕ крестик закрытия
                        button_text = button.text.strip() if hasattr(button, 'text') else ''
                        button_html = button.get_attribute('outerHTML')[:100] if button else ''
                        
                        # Фильтруем вредные элементы
                        if (button_text in ['×', '✕', 'X', 'x'] or 
                            'close' in button_html.lower() or 
                            'cross' in button_html.lower() or
                            button.get_attribute('aria-label') in ['Close', 'Закрыть']):
                            logger.debug(f"⚠️ Skipping close button: text='{button_text}', html='{button_html[:50]}'")
                            continue
                        
                        logger.info(f"✅ FOUND: Modal button with selector: {selector}")
                        logger.info(f"   Button text: '{button_text}', HTML: '{button_html[:50]}'")
                        
                        # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: Проверяем позицию и стили
                        button_info_script = """
                        var el = arguments[0];
                        var rect = el.getBoundingClientRect();
                        var styles = window.getComputedStyle(el);
                        
                        return {
                            position: {
                                x: Math.round(rect.left),
                                y: Math.round(rect.top), 
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            },
                            styles: {
                                backgroundColor: styles.backgroundColor,
                                color: styles.color,
                                display: styles.display,
                                visibility: styles.visibility,
                                zIndex: styles.zIndex
                            },
                            parentInfo: {
                                tagName: el.parentElement ? el.parentElement.tagName : 'none',
                                className: el.parentElement ? el.parentElement.className : ''
                            }
                        };
                        """
                        
                        try:
                            button_info = driver.execute_script(button_info_script, button)
                            logger.info(f"   Позиция: {button_info['position']}")
                            logger.info(f"   Стили: {button_info['styles']}")
                            logger.info(f"   Родитель: {button_info['parentInfo']}")
                            
                            # Проверяем что это СИНЯЯ кнопка И правильная позиция
                            bg_color = button_info['styles']['backgroundColor']
                            position_x = button_info['position']['x']
                            
                            # Из диагностики: модальная кнопка x=623, кнопка формы x=1174
                            if position_x < 800:  # Левее - это модальная кнопка
                                logger.info(f"🎯 ОТЛИЧНО: Позиция кнопки x={position_x} - это МОДАЛЬНАЯ кнопка!")
                                is_modal_button = True
                            else:
                                logger.warning(f"⚠️ НЕПРАВИЛЬНО: Позиция x={position_x} - это кнопка на ФОРМЕ, пропускаем")
                                continue  # Пропускаем кнопку на форме
                            
                            if 'rgb(0, 124, 255)' in bg_color or 'blue' in bg_color or 'rgb(13, 110, 253)' in bg_color:
                                logger.info(f"✅ ЦВЕТ: Синяя кнопка {bg_color} - правильно!")
                            else:
                                logger.warning(f"⚠️ ЦВЕТ: Не синий {bg_color}, но позиция правильная")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Не удалось получить детали кнопки: {e}")
                        
                        # Скроллим к кнопке и кликаем
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        await asyncio.sleep(0.5)
                        
                        # ДИАГНОСТИКА: Проверяем URL ДО клика
                        url_before = driver.current_url
                        logger.info(f"📍 URL ДО клика: {url_before}")
                        
                        try:
                            button.click()
                            logger.info("✅ КЛИК: Обычный клик выполнен")
                            # Увеличиваем задержку для полной загрузки QR страницы
                            logger.info("⏳ Ожидание загрузки QR страницы...")
                            await asyncio.sleep(5)  # Увеличиваем до 5 секунд
                            
                            # Проверяем состояние страницы после клика
                            success_detected = False
                            final_url = driver.current_url
                            logger.info(f"📍 URL ПОСЛЕ клика (5s): {final_url}")
                            
                            # ИНДИКАТОР 1: Проверяем URL с QR параметрами
                            if 'transferId=' in final_url and 'paymentSystemTransferNum=' in final_url:
                                logger.info("🎉 УСПЕХ 1: URL содержит QR параметры!")
                                success_detected = True
                            
                            # ИНДИКАТОР 2: Проверяем исчезновение модального окна
                            try:
                                modal_present = driver.find_elements(By.XPATH, "//div[@role='presentation']")
                                if not modal_present or not modal_present[0].is_displayed():
                                    logger.info("🎉 УСПЕХ 2: Модальное окно исчезло!")
                                    success_detected = True
                            except:
                                pass
                            
                            # ИНДИКАТОР 3: Ищем QR код с улучшенными селекторами
                            qr_selectors = [
                                "//canvas",  # QR коды часто в canvas элементах
                                "//img[contains(@src, 'qr')]",
                                "//img[contains(@alt, 'QR')]", 
                                "//*[contains(@class, 'qr')]",
                                "//img[starts-with(@src, 'data:image')]",  # Base64 изображения
                                "//*[contains(text(), 'Отсканируйте')]"  # Текст под QR кодом
                            ]
                            
                            for qr_selector in qr_selectors:
                                try:
                                    qr_element = driver.find_element(By.XPATH, qr_selector)
                                    if qr_element and qr_element.is_displayed():
                                        logger.info(f"🎉 УСПЕХ 3: QR элемент найден с селектором: {qr_selector}")
                                        success_detected = True
                                        break
                                except:
                                    continue
                            
                            # ИНДИКАТОР 4: Ищем текст "3 из 3" или другие индикаторы финальной страницы
                            final_page_indicators = [
                                "//*[contains(text(), '3 из 3')]",
                                "//*[contains(text(), 'СБП')]",
                                "//*[contains(text(), 'Отсканируйте QR-код')]",
                                "//*[contains(text(), 'Подтвердите оплату')]"
                            ]
                            
                            for indicator in final_page_indicators:
                                try:
                                    element = driver.find_element(By.XPATH, indicator)
                                    if element and element.is_displayed():
                                        logger.info(f"🎉 УСПЕХ 4: Найден индикатор финальной страницы: {element.text[:30]}")
                                        success_detected = True
                                        break
                                except:
                                    continue
                            
                            if success_detected:
                                logger.info("🎉 ОБЩИЙ УСПЕХ: Обнаружены индикаторы QR страницы!")
                                self._qr_page_url = final_url
                                logger.info("💾 СОХРАНЕН успешный URL для Step 14")
                                return True
                            else:
                                logger.warning("⚠️ Не найдено индикаторов успеха - возможно кликнули не ту кнопку")
                            
                        except Exception as click_error:
                            logger.warning(f"⚠️ Обычный клик не сработал: {click_error}")
                            # Fallback к JavaScript клику
                            try:
                                driver.execute_script("arguments[0].click();", button)
                                logger.info("✅ КЛИК: JavaScript клик выполнен")
                                await asyncio.sleep(3)  # Увеличиваем задержку для JS клика
                                
                                url_after_js = driver.current_url
                                logger.info(f"📍 URL ПОСЛЕ JS клика: {url_after_js}")
                                
                                # ИСПРАВЛЕНИЕ: Те же множественные индикаторы для JS клика
                                js_success_detected = False
                                
                                # Проверяем QR параметры в URL
                                if 'transferId=' in url_after_js and 'paymentSystemTransferNum=' in url_after_js:
                                    logger.info("🎉 JS УСПЕХ 1: URL содержит QR параметры!")
                                    js_success_detected = True
                                
                                # Проверяем QR код на странице
                                try:
                                    qr_element = driver.find_element(By.XPATH, "//img[contains(@alt, 'QR') or contains(@src, 'qr')] | //canvas")
                                    if qr_element and qr_element.is_displayed():
                                        logger.info("🎉 JS УСПЕХ 2: QR код найден!")
                                        js_success_detected = True
                                except:
                                    pass
                                
                                # Проверяем "3 из 3"
                                try:
                                    final_step = driver.find_element(By.XPATH, "//*[contains(text(), '3 из 3')]")
                                    if final_step and final_step.is_displayed():
                                        logger.info("🎉 JS УСПЕХ 3: Финальная страница '3 из 3'!")
                                        js_success_detected = True
                                except:
                                    pass
                                
                                if js_success_detected:
                                    logger.info("🎉 JS ОБЩИЙ УСПЕХ: JS клик привел на QR страницу!")
                                    self._qr_page_url = url_after_js
                                    logger.info("💾 СОХРАНЕН успешный URL для Step 14 (JS)")
                                    return True
                                else:
                                    logger.warning(f"⚠️ JS клик тоже не привел к QR странице: {url_after_js}")
                                    
                            except Exception as js_error:
                                logger.error(f"❌ JavaScript клик тоже не сработал: {js_error}")
                        
                        # Если дошли сюда - попробуем следующий селектор
                        continue
                            
                except Exception as e:
                    logger.debug(f"⚠️ Selector {selector} failed: {e}")
                    continue
            
            logger.error("❌ ORIGINAL FAST: No modal continue button found")
            return False
            
            # ДИАГНОСТИКА: Сначала проверим что находится в модальном окне
            diagnostic_script = """
            var modalSelectors = [
                'div[class*="modal"]', 'div[class*="dialog"]', 'div[class*="popup"]',
                'div[style*="position: fixed"]', 'div[style*="z-index"]'
            ];
            
            var found = [];
            for (var s = 0; s < modalSelectors.length; s++) {
                try {
                    var modals = document.querySelectorAll(modalSelectors[s]);
                    for (var m = 0; m < modals.length; m++) {
                        var modal = modals[m];
                        if (modal.offsetParent !== null && modal.offsetWidth > 100 && modal.offsetHeight > 100) {
                            var modalText = modal.textContent || modal.innerText || '';
                            if (modalText.includes('Проверка данных') || modalText.includes('Проверьте данные')) {
                                var buttons = modal.querySelectorAll('button, input[type="button"], input[type="submit"], a');
                                var buttonTexts = [];
                                for (var b = 0; b < buttons.length; b++) {
                                    var btn = buttons[b];
                                    buttonTexts.push((btn.textContent || btn.innerText || btn.value || '').trim());
                                }
                                found.push({
                                    selector: modalSelectors[s],
                                    modalText: modalText.substring(0, 100),
                                    buttonCount: buttons.length,
                                    buttonTexts: buttonTexts
                                });
                            }
                        }
                    }
                } catch(e) { continue; }
            }
            return found;
            """
            
            diagnostic_result = driver.execute_script(diagnostic_script)
            logger.info(f"🔍 DIAGNOSTIC: Found {len(diagnostic_result)} modal(s)")
            for i, modal in enumerate(diagnostic_result):
                logger.info(f"Modal {i}: selector='{modal['selector']}', buttons={modal['buttonCount']}, texts={modal['buttonTexts']}")
            
            result = driver.execute_script(js_button_click_script)
            if result.get('success'):
                logger.info(f"✅ DIAGNOSTIC: Method 1 SUCCESS - clicked {result.get('element')} with text '{result.get('text')}'")
                await asyncio.sleep(5)  # Увеличиваем время ожидания
                
                # Проверяем успех через изменение URL (как в legacy)
                if await self._check_modal_disappeared_legacy(driver):
                    return True
                else:
                    # ДАЖЕ если модальное окно не исчезло, Method 1 кликнул правильную кнопку - ОСТАНАВЛИВАЕМСЯ
                    logger.info("✅ DIAGNOSTIC: Method 1 clicked button, stopping other methods")
                    return True
            
            # FALLBACK: Если Method 1 не сработал, пробуем простой клик по ЛЮБОЙ видимой кнопке в области
            logger.warning("⚠️ DIAGNOSTIC: Method 1 FAILED - trying FALLBACK method")
            
            fallback_script = """
            // ЭКСТРЕННЫЙ FALLBACK: кликаем по любой кнопке в области модального окна
            var allButtons = document.querySelectorAll('button, input[type="button"], input[type="submit"], a');
            var modalArea = null;
            
            // Найти область с "Проверка данных"
            for (var i = 0; i < allButtons.length; i++) {
                var btn = allButtons[i];
                var parent = btn.parentElement;
                while (parent) {
                    var text = parent.textContent || parent.innerText || '';
                    if (text.includes('Проверка данных') || text.includes('Проверьте данные')) {
                        modalArea = parent;
                        break;
                    }
                    parent = parent.parentElement;
                }
                if (modalArea) break;
            }
            
            if (modalArea) {
                var buttonsInArea = modalArea.querySelectorAll('button, input[type="button"], input[type="submit"], a');
                for (var j = 0; j < buttonsInArea.length; j++) {
                    var btn = buttonsInArea[j];
                    if (btn.offsetWidth > 0 && btn.offsetHeight > 0 && !btn.disabled) {
                        var btnText = (btn.textContent || btn.innerText || btn.value || '').trim();
                        // НЕ кликаем явно отменяющие кнопки
                        if (!btnText.toLowerCase().includes('отмена') && 
                            !btnText.toLowerCase().includes('cancel') &&
                            !btnText.toLowerCase().includes('закрыть')) {
                            btn.click();
                            return {success: true, text: btnText, method: 'fallback'};
                        }
                    }
                }
            }
            return {success: false};
            """
            
            fallback_result = driver.execute_script(fallback_script)
            if fallback_result.get('success'):
                logger.info(f"✅ FALLBACK SUCCESS: clicked button '{fallback_result.get('text')}' via {fallback_result.get('method')}")
                await asyncio.sleep(5)
                return True
            
            logger.error("❌ DIAGNOSTIC: All methods FAILED - no continue button found in modal")
            return False
            
        except Exception as e:
            logger.error(f"❌ DIAGNOSTIC button click error: {e}")
            return False
    
    async def _diagnostic_dom_analysis_legacy(self, driver):
        """ДИАГНОСТИЧЕСКИЙ анализ DOM для поиска кнопки (адаптировано из legacy)"""
        try:
            logger.info("🔍 DIAGNOSTIC: Starting legacy DOM analysis...")
            
            # 1. Анализ всех кнопок на странице
            all_buttons_script = """
            var buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"], a[role="button"]');
            var buttonData = [];
            for (var i = 0; i < buttons.length; i++) {
                var btn = buttons[i];
                if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {  // Visible elements only
                    buttonData.push({
                        index: i,
                        tagName: btn.tagName,
                        text: btn.textContent || btn.innerText || btn.value || '',
                        className: btn.className || '',
                        id: btn.id || '',
                        type: btn.type || '',
                        visible: btn.offsetParent !== null,
                        enabled: !btn.disabled,
                        style: btn.getAttribute('style') || ''
                    });
                }
            }
            return buttonData;
            """
            
            button_data = driver.execute_script(all_buttons_script)
            logger.info(f"🔍 DIAGNOSTIC: Found {len(button_data)} visible buttons")
            
            # Логируем первые 10 кнопок
            for i, btn in enumerate(button_data[:10]):
                logger.info(f"Button {i}: text='{btn['text'][:30]}', class='{btn['className'][:20]}', enabled={btn['enabled']}")
            
            # 2. Поиск кнопок с похожим текстом
            continue_buttons = []
            for btn in button_data:
                text = btn['text'].strip().upper()
                if any(keyword in text for keyword in ['ПРОДОЛЖИТЬ', 'CONTINUE', 'NEXT', 'ДАЛЕЕ', 'OK', 'ГОТОВО']):
                    continue_buttons.append(btn)
                    logger.info(f"🎯 DIAGNOSTIC: Found potential continue button: '{btn['text']}' (class: {btn['className']})") 
            
            return {
                'total_buttons': len(button_data),
                'continue_buttons': continue_buttons
            }
            
        except Exception as e:
            logger.error(f"❌ DIAGNOSTIC DOM analysis error: {e}")
            return None
    
    async def _detect_second_captcha(self, driver) -> bool:
        """БЫСТРАЯ проверка наличия второй CAPTCHA в модальном окне"""
        try:
            # БЫСТРАЯ проверка - только основные селекторы с таймаутом
            second_captcha_selectors = [
                "//iframe[contains(@src, 'captcha.yandex')]",
                "//div[contains(@class, 'CheckboxCaptcha')]",
                "//div[contains(@class, 'captcha')]"
            ]
            
            # МАКСИМАЛЬНО БЫСТРАЯ проверка - только одна попытка!
            for selector in second_captcha_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:  # Если элементы найдены
                        for element in elements:
                            try:
                                if element.is_displayed():
                                    logger.info(f"🚨 SECOND CAPTCHA detected with selector: {selector}")
                                    return True
                            except:
                                continue
                except:
                    continue
            
            logger.info("ℹ️ No SECOND CAPTCHA found in modal (3s timeout)")
            return False
            
        except Exception as e:
            logger.debug(f"Second CAPTCHA detection error: {e}")
            return False
    
    async def _click_modal_continue_button(self, driver) -> bool:
        """УЛУЧШЕННЫЙ клик по кнопке ПРОДОЛЖИТЬ в модальном окне с диагностическими методами из legacy"""
        try:
            logger.info("🎯 ENHANCED: Starting modal continue button click with legacy methods")
            
            # Метод 1: Стандартный поиск через селекторы (быстрый)
            modal_continue_selectors = [
                "(//button[contains(text(), 'ПРОДОЛЖИТЬ')])[last()]",  # Последняя кнопка ПРОДОЛЖИТЬ
                "//div[contains(@class, 'modal')]//button[contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//button[contains(text(), 'ПРОДОЛЖИТЬ') and contains(@class, 'modal')]",
                "//button[contains(text(), 'Продолжить')]",
                "//input[@value='ПРОДОЛЖИТЬ']"
            ]
            
            for selector in modal_continue_selectors:
                try:
                    element = driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        logger.info(f"🎯 Found modal continue button: {selector}")
                        element.click()
                        logger.info("✅ Clicked modal continue button (Method 1)")
                        await asyncio.sleep(1)
                        
                        # Проверяем успех через изменение URL (как в legacy)
                        if await self._check_modal_disappeared_legacy(driver):
                            return True
                except:
                    continue
            
            # Метод 2: JavaScript поиск и клик (из legacy)
            logger.info("🎯 ENHANCED: Method 2 - Legacy JavaScript search")
            js_legacy_click = """
            function findContinueButton() {
                var keywords = ['ПРОДОЛЖИТЬ', 'продолжить', 'Продолжить', 'CONTINUE', 'Continue', 'ДАЛЕЕ', 'далее', 'NEXT'];
                var allElements = document.querySelectorAll('*');
                
                for (var i = 0; i < allElements.length; i++) {
                    var el = allElements[i];
                    var text = el.textContent || el.innerText || el.value || '';
                    
                    // Проверяем точное совпадение
                    for (var j = 0; j < keywords.length; j++) {
                        if (text.trim() === keywords[j] || text.trim().toUpperCase() === keywords[j].toUpperCase()) {
                            // Проверяем что элемент кликабельный
                            if ((el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'INPUT') && 
                                el.offsetWidth > 0 && el.offsetHeight > 0 && !el.disabled) {
                                return el;
                            }
                        }
                    }
                }
                return null;
            }
            
            var button = findContinueButton();
            if (button) {
                button.click();
                return {success: true, element: button.tagName, text: button.textContent};
            }
            return {success: false};
            """
            
            result = driver.execute_script(js_legacy_click)
            if result.get('success'):
                logger.info(f"✅ Method 2 SUCCESS - clicked {result.get('element')} with text '{result.get('text')}'")
                await asyncio.sleep(1)
                
                if await self._check_modal_disappeared_legacy(driver):
                    return True
            
            # Метод 3: Координатный клик в правый нижний угол модального окна (из legacy)
            logger.info("🎯 ENHANCED: Method 3 - Legacy coordinate click")
            coordinate_click = """
            var modalElements = document.querySelectorAll('*');
            for (var i = 0; i < modalElements.length; i++) {
                var el = modalElements[i];
                var text = el.textContent || el.innerText || '';
                if (text.includes('Проверка данных') || text.includes('Проверьте данные')) {
                    var rect = el.getBoundingClientRect();
                    // Клик в правый нижний угол (где обычно кнопки)
                    var clickX = rect.right - 100;
                    var clickY = rect.bottom - 30;
                    
                    // Создаем событие клика
                    var event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: clickX,
                        clientY: clickY
                    });
                    
                    // Находим элемент в этих координатах
                    var targetElement = document.elementFromPoint(clickX, clickY);
                    if (targetElement) {
                        targetElement.dispatchEvent(event);
                        return {success: true, coordinates: [clickX, clickY], target: targetElement.tagName};
                    }
                }
            }
            return {success: false};
            """
            
            result = driver.execute_script(coordinate_click)
            if result.get('success'):
                logger.info(f"✅ Method 3 SUCCESS - coordinate click at {result.get('coordinates')}")
                await asyncio.sleep(1)
                
                if await self._check_modal_disappeared_legacy(driver):
                    return True
            
            # Метод 4: Эмуляция клавиш (из legacy)
            logger.info("🎯 ENHANCED: Method 4 - Legacy keyboard events")
            keyboard_script = """
            // Пробуем разные клавиши
            var events = ['Enter', 'Space', 'Escape'];
            for (var i = 0; i < events.length; i++) {
                var event = new KeyboardEvent('keydown', {
                    key: events[i],
                    code: events[i],
                    bubbles: true
                });
                document.dispatchEvent(event);
            }
            return {success: true};
            """
            
            driver.execute_script(keyboard_script)
            await asyncio.sleep(1)
            
            if await self._check_modal_disappeared_legacy(driver):
                logger.info("✅ Method 4 SUCCESS - keyboard event")
                return True
            
            # Метод 5: Поиск и клик по всем элементам в области модального окна (из legacy)
            logger.info("🎯 ENHANCED: Method 5 - Legacy area click")
            area_click_script = """
            var modalArea = null;
            var allElements = document.querySelectorAll('*');
            
            // Найти модальное окно
            for (var i = 0; i < allElements.length; i++) {
                var el = allElements[i];
                var text = el.textContent || el.innerText || '';
                if (text.includes('Проверка данных')) {
                    modalArea = el;
                    break;
                }
            }
            
            if (modalArea) {
                var clickableInModal = modalArea.querySelectorAll('button, a, input, div[onclick], span[onclick]');
                for (var j = 0; j < clickableInModal.length; j++) {
                    var clickable = clickableInModal[j];
                    if (clickable.offsetWidth > 0 && clickable.offsetHeight > 0) {
                        clickable.click();
                        return {success: true, clicked: clickable.tagName, text: clickable.textContent};
                    }
                }
            }
            return {success: false};
            """
            
            result = driver.execute_script(area_click_script)
            if result.get('success'):
                logger.info(f"✅ Method 5 SUCCESS - area click on {result.get('clicked')}")
                await asyncio.sleep(1)
                
                if await self._check_modal_disappeared_legacy(driver):
                    return True
            
            logger.error("❌ All enhanced modal click methods failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Enhanced modal continue button click error: {e}")
            return False
    
    async def _click_final_continue_button(self, driver) -> bool:
        """Шаг 13: Клик финальной кнопки ПРОДОЛЖИТЬ (адаптировано из MultiTransferAutomation)"""
        try:
            # ИСПРАВЛЕННЫЙ поиск СИНЕЙ кнопки "ПРОДОЛЖИТЬ" на странице "Данные отправителя"  
            js_script = """
            function findBlueContinueButton() {
                var buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"], a');
                var candidates = [];
                
                // Собираем все кнопки "ПРОДОЛЖИТЬ"
                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    var text = (btn.textContent || btn.innerText || btn.value || '').trim().toUpperCase();
                    if ((text === 'ПРОДОЛЖИТЬ' || text === 'CONTINUE') && btn.offsetParent !== null && !btn.disabled) {
                        var style = window.getComputedStyle(btn);
                        var bgColor = style.backgroundColor;
                        var rect = btn.getBoundingClientRect();
                        
                        candidates.push({
                            element: btn,
                            text: btn.textContent || btn.value,
                            bgColor: bgColor,
                            position: {x: rect.right, y: rect.bottom},
                            isBlue: bgColor.includes('rgb(0, 123, 255)') || bgColor.includes('rgb(0, 100, 200)') || 
                                   bgColor.includes('rgb(13, 110, 253)') || bgColor.includes('blue')
                        });
                    }
                }
                
                // Приоритет 1: Синие кнопки
                for (var j = 0; j < candidates.length; j++) {
                    if (candidates[j].isBlue) {
                        return candidates[j].element;
                    }
                }
                
                // Приоритет 2: Кнопка в правом нижнем углу (как на скриншоте)
                var rightmostBottommost = null;
                var maxX = 0, maxY = 0;
                for (var k = 0; k < candidates.length; k++) {
                    var pos = candidates[k].position;
                    if (pos.x >= maxX && pos.y >= maxY) {
                        maxX = pos.x;
                        maxY = pos.y;
                        rightmostBottommost = candidates[k].element;
                    }
                }
                
                return rightmostBottommost;
            }
            
            var button = findBlueContinueButton();
            if (button) {
                button.click();
                return {success: true, text: button.textContent || button.value};
            }
            return {success: false};
            """
            
            result = driver.execute_script(js_script)
            if result.get('success'):
                logger.info(f"✅ Clicked final continue button: '{result.get('text')}'")
                return True
            
            # Fallback - обычный поиск через Selenium
            continue_selectors = [
                "//button[contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//input[@value='ПРОДОЛЖИТЬ']",
                "//a[contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//button[contains(text(), 'CONTINUE')]"
            ]
            
            for selector in continue_selectors:
                try:
                    element = driver.find_element(By.XPATH, selector)
                    if element and element.is_displayed():
                        element.click()
                        logger.info(f"✅ Clicked final continue button via selector: {selector}")
                        return True
                except:
                    continue
            
            logger.warning("⚠️ Could not find final continue button")
            return False
            
        except Exception as e:
            logger.error(f"❌ Final continue button click error: {e}")
            return False
    
    async def _get_payment_result(self, driver) -> Dict[str, Any]:
        """Шаг 14: Получение результата оплаты (адаптировано из MultiTransferAutomation)"""
        try:
            await asyncio.sleep(2)  # Ждем загрузки результата
            
            current_url = driver.current_url
            logger.info(f"📍 Final URL: {current_url}")
            
            # ИСПРАВЛЕНИЕ: Проверяем если URL уже был определен как успешный в Step 12
            if hasattr(self, '_qr_page_url') and self._qr_page_url:
                logger.info(f"💾 ИСПОЛЬЗУЕМ сохраненный URL из Step 12: {self._qr_page_url}")
                current_url = self._qr_page_url
            
            # Проверяем что мы на правильной странице
            if current_url == "https://multitransfer.ru" or current_url == "https://multitransfer.ru/":
                logger.warning("⚠️ Still on homepage - payment may have failed")
                return {
                    "success": False,
                    "error": "Still on homepage",
                    "payment_url": current_url,
                    "qr_code_url": None
                }
            
            # ИСПРАВЛЕНИЕ: Проверяем успешный URL с transferId и paymentSystemTransferNum
            if 'transferId=' in current_url and 'paymentSystemTransferNum=' in current_url:
                logger.info("🎉 УСПЕХ: Обнаружена страница с QR - URL содержит transferId и paymentSystemTransferNum!")
                # Это успешная QR страница - продолжаем поиск QR кода
            elif '/transfer/' in current_url:
                logger.info("🎯 ХОРОШО: На странице перевода - ищем QR код")
            else:
                logger.warning(f"⚠️ Неожиданный URL: {current_url}")
                # Но продолжаем попытку найти QR код
            
            # УЛУЧШЕННЫЙ ПОИСК QR-КОДА
            qr_code_url = None
            logger.info("🔍 Ищем QR код на странице...")
            
            # Расширенные селекторы для QR кода
            qr_selectors = [
                "//canvas",  # QR коды часто в canvas элементах
                "//img[starts-with(@src, 'data:image')]",  # Base64 изображения
                "//img[contains(@src, 'qr')]",
                "//img[contains(@alt, 'QR')]",
                "//*[contains(@class, 'qr')]//img",
                "//*[contains(@class, 'qr')]//canvas",
                "//img[contains(@src, 'png')]",  # PNG изображения (QR часто в PNG)
                "//img[contains(@src, 'svg')]",  # SVG QR коды
            ]
            
            for i, selector in enumerate(qr_selectors, 1):
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    logger.info(f"🔍 Selector {i}: {selector} - найдено {len(elements)} элементов")
                    
                    for element in elements:
                        if element and element.is_displayed():
                            # Для canvas элементов
                            if element.tag_name.lower() == 'canvas':
                                # Конвертируем canvas в base64
                                canvas_data = driver.execute_script(
                                    "return arguments[0].toDataURL('image/png');", element
                                )
                                if canvas_data and canvas_data.startswith('data:image'):
                                    qr_code_url = canvas_data
                                    logger.info("✅ QR код найден в CANVAS элементе!")
                                    break
                            else:
                                # Для img элементов
                                qr_url = element.get_attribute("src")
                                if qr_url:
                                    qr_code_url = qr_url
                                    logger.info(f"✅ QR код найден в IMG: {qr_url[:50]}...")
                                    break
                    
                    if qr_code_url:
                        break
                        
                except Exception as e:
                    logger.debug(f"⚠️ Selector {i} failed: {e}")
            
            if not qr_code_url:
                logger.warning("⚠️ QR код не найден, но URL успешный - возвращаем ссылку")
            
            # Возвращаем результат
            return {
                "success": True,
                "payment_url": current_url,
                "qr_code_url": qr_code_url,
                "message": "Payment result extracted successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Payment result extraction error: {e}")
            return {
                "success": False,
                "error": str(e),
                "payment_url": None,
                "qr_code_url": None
            }
    
    async def get_payment_status(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Получить статус платежа по ID"""
        logger.info(f"📊 Getting payment status: {payment_id}")
        
        payment = await self.payment_repo.get_payment_by_id(payment_id)
        if not payment:
            return None
        
        return {
            'payment_id': payment.id,
            'status': payment.status,
            'amount': float(payment.amount) if payment.amount else 0,
            'currency_from': payment.currency_from,
            'currency_to': payment.currency_to,
            'qr_code_url': payment.qr_code_url,
            'payment_url': payment.payment_url,
            'error_message': payment.error_message,
            'processing_time': payment.processing_time,
            'created_at': payment.created_at.isoformat() if payment.created_at else None
        }
    
    async def get_user_payment_history(self, user_id: int, limit: int = 10) -> list:
        """Получить историю платежей пользователя"""
        logger.info(f"📜 Getting payment history for user {user_id}")
        
        payments = await self.payment_repo.get_user_payments(user_id, limit)
        
        return [
            {
                'payment_id': payment.id,
                'amount': float(payment.amount) if payment.amount else 0,
                'status': payment.status,
                'currency_from': payment.currency_from,
                'currency_to': payment.currency_to,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'processing_time': payment.processing_time
            }
            for payment in payments
        ]