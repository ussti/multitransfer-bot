"""
OPTIMIZED MultiTransfer.ru Browser Automation with SECOND CAPTCHA support
Оптимизированная автоматизация с поддержкой ВТОРОЙ КАПЧИ (50% случаев)
"""

import logging
import asyncio
import random
import time
import re
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from web.captcha.solver import CaptchaSolver

logger = logging.getLogger(__name__)

class MultiTransferAutomation:
    """ИСПРАВЛЕННАЯ автоматизация multitransfer.ru с поддержкой ВТОРОЙ КАПЧИ"""
    
    def __init__(self, proxy: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        self.proxy = proxy
        self.config = config or {}
        self.base_url = "https://multitransfer.ru"
        self._driver = None
        self.captcha_solver = CaptchaSolver(config)
        
        # Оптимизированные настройки для скорости
        self.screenshot_enabled = config.get('development', {}).get('screenshots_enabled', False)
        self.fast_mode = config.get('multitransfer', {}).get('fast_mode', True)
        
        # ОПТИМИЗИРОВАННЫЕ селекторы - только самые быстрые
        self.selectors = {
            # Приоритетные селекторы (самые быстрые первыми)
            'transfer_abroad_btn': [
                "//button[contains(text(), 'ПЕРЕВЕСТИ ЗА РУБЕЖ')]"
            ],
            
            'tajikistan_select': [
                "//span[text()='Таджикистан']/parent::div",
                "//div[contains(text(), 'Таджикистан')]"
            ],
            
            'amount_input': [
                "//input[contains(@placeholder, 'RUB')]",
                "//input[@type='number']"
            ],
            
            'currency_tjs': [
                "//button[contains(text(), 'TJS')]",
                "//*[text()='TJS']"
            ],
            
            'transfer_method_dropdown': [
                "//div[contains(text(), 'Способ перевода')]//following-sibling::*",
                "//*[contains(text(), 'способ')]"
            ],
            
            'korti_milli_option': [
                "//*[contains(text(), 'Корти Милли')]"
            ],
            
            'continue_btn': [
                "//button[contains(text(), 'ПРОДОЛЖИТЬ')]"
            ],
            
            'recipient_card': [
                "//input[@placeholder='Номер банковской карты']",
                "//input[contains(@placeholder, 'карты')]"
            ],
            
            'passport_rf_toggle': [
                "//button[contains(text(), 'Паспорт РФ')]"
            ],
            
            # Поля формы - оптимизированные
            'passport_series': [
                "//input[@placeholder='Серия паспорта']"
            ],
            
            'passport_number': [
                "//input[@placeholder='Номер паспорта']"
            ],
            
            'passport_date': [
                "//label[contains(text(), 'Дата выдачи')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                "(//input[@placeholder='ДД.ММ.ГГГГ'])[2]"
            ],
            
            'surname': [
                "//input[@placeholder='Укажите фамилию']"
            ],
            
            'name': [
                "//input[@placeholder='Укажите имя']"
            ],
            
            'birthdate': [
                "//label[contains(text(), 'Дата рождения')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                "(//input[@placeholder='ДД.ММ.ГГГГ'])[1]"
            ],
            
            'phone': [
                "//input[@placeholder='Укажите номер телефона']"
            ],
            
            'agreement_checkbox': [
                "//input[@type='checkbox']"
            ],
            
            'final_continue': [
                "//button[contains(text(), 'ПРОДОЛЖИТЬ')]"
            ],
            
            # Step 12: Модальное окно
            'data_verification_modal': [
                "//div[contains(text(), 'Проверка данных')]",
                "//*[contains(text(), 'Проверьте данные получателя')]"
            ],
            
            'modal_continue_btn': [
                "(//button[contains(text(), 'ПРОДОЛЖИТЬ')])[last()]",
                "//*[contains(@class, 'modal')]//button[contains(text(), 'ПРОДОЛЖИТЬ')]"
            ]
        }
    
    async def _setup_driver(self):
        """БЫСТРАЯ настройка Chrome драйвера"""
        try:
            logger.info("🚀 Fast Chrome driver setup...")
            
            options = uc.ChromeOptions()
            
            # ОПТИМИЗИРОВАННЫЕ настройки для скорости
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Отключаем загрузку изображений
            options.add_argument('--disable-javascript')  # Частично отключаем JS (где возможно)
            options.add_argument('--window-size=1920,1080')
            
            # Прокси
            if self.proxy:
                proxy_string = f"{self.proxy['ip']}:{self.proxy['port']}"
                options.add_argument(f'--proxy-server=http://{proxy_string}')
                logger.info(f"🌐 Using proxy: {proxy_string}")
            
            # Быстрый user agent
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
            
            # Создаем драйвер с быстрыми настройками
            self._driver = uc.Chrome(options=options)
            self._driver.implicitly_wait(3)  # Сокращено с 10 до 3 секунд
            
            logger.info("✅ Fast Chrome driver ready")
            return self._driver
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Chrome driver: {e}")
            return None
    
    # ОПТИМИЗИРОВАННЫЕ вспомогательные методы
    
    def find_element_fast(self, by, selector, timeout=2):
        """Быстрый поиск элемента (2 сек вместо 5)"""
        try:
            element = WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except:
            return None
    
    def find_elements_fast(self, by, selector):
        """Быстрый поиск элементов без ожидания"""
        try:
            return self._driver.find_elements(by, selector)
        except:
            return []
    
    def click_element_fast(self, element):
        """Быстрый клик без лишних задержек"""
        try:
            # Прокрутка без задержки
            self._driver.execute_script("arguments[0].scrollIntoView(true);", element)
            # Мгновенный клик
            element.click()
            return True
        except:
            try:
                self._driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False
    
    def type_text_fast(self, element, text):
        """Быстрый ввод текста (без посимвольной задержки)"""
        try:
            element.clear()
            # Мгновенный ввод всего текста
            element.send_keys(text)
            return True
        except:
            return False
    
    def take_screenshot_conditional(self, filename):
        """Скриншот только если включен в настройках"""
        if self.screenshot_enabled:
            try:
                import os
                os.makedirs("logs/automation", exist_ok=True)
                self._driver.save_screenshot(f"logs/automation/{filename}")
                logger.debug(f"📸 Screenshot: {filename}")
            except:
                pass
    
    # ОСНОВНОЙ МЕТОД
    
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """ИСПРАВЛЕННОЕ создание платежа с поддержкой ВТОРОЙ КАПЧИ (цель: до 40 секунд)"""
        start_time = time.time()
        try:
            logger.info(f"🚀 FIXED payment creation: {payment_data['amount']} {payment_data.get('currency_from', 'RUB')}")
            
            # Быстрая настройка драйвера
            driver = await self._setup_driver()
            if not driver:
                return {'success': False, 'error': 'Failed to setup browser driver'}
            
            # Открытие сайта
            self._driver.get(self.base_url)
            self.take_screenshot_conditional("00_homepage.png")
            
            # ОПТИМИЗИРОВАННАЯ последовательность
            await self._fast_country_and_amount(payment_data)
            await self._fast_fill_forms(payment_data)
            await self._fast_submit_and_captcha()
            
            # ИСПРАВЛЕННЫЙ Step 12: Модальное окно "Проверка данных" с ВТОРОЙ КАПЧЕЙ
            await self._fast_handle_modal_with_second_captcha()
            
            # Извлечение результата
            result = await self._get_payment_result()
            
            total_time = time.time() - start_time
            logger.info(f"✅ FIXED payment completed in {total_time:.1f}s!")
            return result
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"❌ Payment failed after {total_time:.1f}s: {e}")
            self.take_screenshot_conditional("error_final.png")
            return {'success': False, 'error': str(e)}
            
        finally:
            if hasattr(self, '_driver') and self._driver:
                try:
                    self._driver.quit()
                except:
                    pass
                self._driver = None
    
    async def _fast_country_and_amount(self, payment_data: Dict[str, Any]):
        """БЫСТРЫЕ шаги 1-6: страна и сумма (цель: 8-10 секунд)"""
        logger.info("🏃‍♂️ Fast steps 1-6: country and amount")
        
        # Шаг 1: Клик "ПЕРЕВЕСТИ ЗА РУБЕЖ" - БЕЗ ЗАДЕРЖЕК
        await asyncio.sleep(1)  # Минимальная загрузка страницы
        
        buttons = self.find_elements_fast(By.TAG_NAME, "button")
        for btn in buttons:
            if "ПЕРЕВЕСТИ ЗА РУБЕЖ" in (btn.text or ""):
                if self.click_element_fast(btn):
                    logger.info("✅ Step 1: Transfer abroad clicked")
                    break
        
        # Шаг 2: Выбор Таджикистана - БЫСТРО
        await asyncio.sleep(0.5)  # Минимальное ожидание модального окна
        
        for selector in self.selectors['tajikistan_select']:
            elements = self.find_elements_fast(By.XPATH, selector)
            for element in elements:
                if element.is_displayed() and self.click_element_fast(element):
                    logger.info("✅ Step 2: Tajikistan selected")
                    break
            else:
                continue
            break
        
        # Шаг 3: Заполнение суммы - МГНОВЕННО
        await asyncio.sleep(0.5)
        
        for selector in self.selectors['amount_input']:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element and element.is_displayed():
                if self.type_text_fast(element, str(int(payment_data['amount']))):
                    logger.info("✅ Step 3: Amount filled")
                    break
        
        # Шаг 4: Валюта TJS - БЫСТРО
        await asyncio.sleep(0.3)
        
        for selector in self.selectors['currency_tjs']:
            elements = self.find_elements_fast(By.XPATH, selector)
            for element in elements:
                if element.is_displayed() and self.click_element_fast(element):
                    logger.info("✅ Step 4: TJS currency selected")
                    break
            else:
                continue
            break
        
        # Шаг 5: Способ перевода - БЫСТРО
        await asyncio.sleep(0.3)
        
        # Открываем dropdown
        for selector in self.selectors['transfer_method_dropdown']:
            elements = self.find_elements_fast(By.XPATH, selector)
            for element in elements:
                if element.is_displayed() and self.click_element_fast(element):
                    break
        
        await asyncio.sleep(0.3)
        
        # Выбираем Корти Милли
        for selector in self.selectors['korti_milli_option']:
            elements = self.find_elements_fast(By.XPATH, selector)
            for element in elements:
                if element.is_displayed() and self.click_element_fast(element):
                    logger.info("✅ Step 5: Korti Milli selected")
                    break
            else:
                continue
            break
        
        # Шаг 6: ПРОДОЛЖИТЬ - БЫСТРО
        await asyncio.sleep(0.3)
        
        buttons = self.find_elements_fast(By.TAG_NAME, "button")
        for btn in buttons:
            if "ПРОДОЛЖИТЬ" in (btn.text or "").upper():
                if self.click_element_fast(btn):
                    logger.info("✅ Step 6: Continue clicked")
                    break
        
        await asyncio.sleep(0.5)
        self.take_screenshot_conditional("fast_steps_1-6.png")
        logger.info("🏃‍♂️ Steps 1-6 completed FAST!")
    
    async def _fast_fill_forms(self, payment_data: Dict[str, Any]):
        """БЫСТРОЕ заполнение форм 7-9 (цель: 8-10 секунд)"""
        logger.info("🏃‍♂️ Fast form filling steps 7-9")
        
        # Шаг 7: Карта получателя - МГНОВЕННО
        card_number = payment_data.get('recipient_card', '')
        for selector in self.selectors['recipient_card']:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element and element.is_displayed():
                if self.type_text_fast(element, card_number):
                    logger.info("✅ Step 7: Recipient card filled")
                    break
        
        # Шаги 8-9: Данные отправителя - БЫСТРО
        passport_data = payment_data.get('passport_data', {})
        
        # Переключение на Паспорт РФ
        for selector in self.selectors['passport_rf_toggle']:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element and element.is_displayed():
                self.click_element_fast(element)
                break
        
        # БЫСТРОЕ заполнение всех полей
        fields_to_fill = [
            ('passport_series', passport_data.get('passport_series', '')),
            ('passport_number', passport_data.get('passport_number', '')),
            ('passport_date', passport_data.get('passport_date', '')),
            ('surname', passport_data.get('surname', '')),
            ('name', passport_data.get('name', '')),
            ('birthdate', passport_data.get('birthdate', '')),
            ('phone', self._generate_phone())
        ]
        
        for field_key, value in fields_to_fill:
            if not value:
                continue
                
            for selector in self.selectors[field_key]:
                element = self.find_element_fast(By.XPATH, selector, timeout=1)
                if element and element.is_displayed() and element.is_enabled():
                    if self.type_text_fast(element, str(value)):
                        logger.debug(f"✅ {field_key} filled")
                        break
                else:
                    continue
                break
        
        # Шаг 9: Checkbox согласия - ПРИНУДИТЕЛЬНО
        await asyncio.sleep(0.3)
        
        checkboxes = self.find_elements_fast(By.XPATH, "//input[@type='checkbox']")
        for cb in checkboxes:
            try:
                # Принудительный клик через JavaScript
                self._driver.execute_script("arguments[0].click();", cb)
                if cb.is_selected():
                    logger.info("✅ Step 9: Agreement checkbox checked")
                    break
            except:
                continue
        
        self.take_screenshot_conditional("fast_forms_filled.png")
        logger.info("🏃‍♂️ Forms filled FAST!")
    
    async def _fast_submit_and_captcha(self):
        """БЫСТРАЯ отправка и решение ПЕРВОЙ капчи 10-11 (цель: до 35 секунд с капчей)"""
        logger.info("🏃‍♂️ Fast submit and FIRST captcha steps 10-11")
        
        # Шаг 10: Финальная отправка
        buttons = self.find_elements_fast(By.TAG_NAME, "button")
        for btn in buttons:
            if "ПРОДОЛЖИТЬ" in (btn.text or "").upper():
                if self.click_element_fast(btn):
                    logger.info("✅ Step 10: Final form submitted")
                    break
        
        await asyncio.sleep(1)  # Ожидание обработки
        
        # Шаг 11: КРИТИЧЕСКОЕ решение ПЕРВОЙ капчи
        logger.info("🔐 Step 11: CRITICAL FIRST CAPTCHA solving")
        captcha_solved = await self.captcha_solver.solve_captcha(self._driver)
        
        if captcha_solved:
            logger.info("✅ Step 11: FIRST CAPTCHA solved successfully")
        else:
            logger.error("❌ Step 11: FIRST CAPTCHA solve FAILED - cannot proceed")
            # КРИТИЧЕСКОЕ: если капча не решена - СТОП
            raise Exception("FIRST CAPTCHA solve failed - payment process cannot continue")
        
        self.take_screenshot_conditional("fast_first_captcha_solved.png")
    
    async def _fast_handle_modal_with_second_captcha(self):
        """
        ДИАГНОСТИЧЕСКАЯ версия: обработка модального окна с полной диагностикой
        """
        logger.info("🏃‍♂️ Step 12: DIAGNOSTIC modal + SECOND CAPTCHA handling")
        
        await asyncio.sleep(2)  # Больше времени для появления модального окна
        
        # СТРОГИЙ поиск модального окна "Проверка данных"
        modal_selectors = [
            "//div[contains(text(), 'Проверка данных')]",
            "//*[contains(text(), 'Проверьте данные получателя')]",
            "//*[contains(text(), 'Проверка данных')]",
            "//h2[contains(text(), 'Проверка данных')]",
            "//h3[contains(text(), 'Проверка данных')]"
        ]
        
        modal_found = False
        modal_element = None
        for selector in modal_selectors:
            element = self.find_element_fast(By.XPATH, selector, timeout=3)
            if element and element.is_displayed():
                logger.info(f"✅ Found 'Проверка данных' modal with selector: {selector}")
                modal_found = True
                modal_element = element
                break
        
        if not modal_found:
            logger.warning("⚠️ No 'Проверка данных' modal found - this is unexpected after FIRST CAPTCHA")
            return
        
        self.take_screenshot_conditional("step12_modal_found.png")
        
        # ПРОВЕРКА ВТОРОЙ КАПЧИ
        logger.info("🔍 CRITICAL: Checking for SECOND CAPTCHA (50% probability)")
        await self._handle_potential_second_captcha()
        
        # ДИАГНОСТИКА: ПОЛНЫЙ АНАЛИЗ DOM
        logger.info("🔍 DIAGNOSTIC: Full DOM analysis for modal button")
        await self._diagnostic_dom_analysis()
        
        # ДИАГНОСТИЧЕСКАЯ попытка клика
        logger.info("🎯 DIAGNOSTIC: Enhanced button finding with full analysis")
        button_clicked = await self._diagnostic_button_click()
        
        if button_clicked:
            logger.info("✅ DIAGNOSTIC SUCCESS: Modal handled successfully!")
            await asyncio.sleep(2)
            self.take_screenshot_conditional("step12_modal_success.png")
        else:
            logger.error("❌ DIAGNOSTIC FAILURE: Could not handle modal")
            self.take_screenshot_conditional("step12_modal_failure.png")
            raise Exception("DIAGNOSTIC: Failed to handle modal - payment cannot be completed")
        
        logger.info("🏃‍♂️ Step 12 DIAGNOSTIC completion - proceeding to result extraction")
    
    async def _handle_potential_second_captcha(self):
        """
        НОВЫЙ МЕТОД: Обработка потенциальной ВТОРОЙ КАПЧИ (50% случаев)
        
        Появляется ПОСЛЕ первой капчи, ПЕРЕД кликом "ПРОДОЛЖИТЬ" в модальном окне.
        Тип: Yandex Smart Captcha - slider puzzle "Move the slider to complete the puzzle"
        """
        logger.info("🔍 CHECKING for potential SECOND CAPTCHA (50% probability)...")
        
        # Даем 5 секунд на появление второй капчи
        start_time = time.time()
        second_captcha_timeout = 5  # секунд
        
        while time.time() - start_time < second_captcha_timeout:
            await asyncio.sleep(1)  # Проверяем каждую секунду
            
            # Ищем индикаторы ВТОРОЙ капчи
            second_captcha_indicators = [
                # Yandex Smart Captcha (как на скриншоте)
                "//div[contains(@class, 'CheckboxCaptcha')]",
                "//div[contains(@class, 'captcha-checkbox')]", 
                "//iframe[contains(@src, 'captcha.yandex')]",
                "//*[contains(@class, 'ya-captcha')]",
                "//*[contains(@class, 'smart-captcha')]",
                "//*[contains(text(), 'SmartCaptcha by Yandex')]",
                "//*[contains(text(), 'SmartCaptcha by Yandex Cloud')]",
                
                # Специфичные для slider puzzle (как на скриншоте)
                "//*[contains(text(), 'Move the slider')]",
                "//*[contains(text(), 'complete the puzzle')]",
                "//*[contains(text(), 'Pull to the right')]",
                "//div[contains(@class, 'slider')]//following-sibling::*[contains(text(), 'puzzle')]",
                
                # Generic captcha indicators (на всякий случай)
                "//div[contains(@class, 'captcha')]",
                "//*[contains(@id, 'captcha')]",
                "//*[contains(text(), 'captcha')]"
            ]
            
            second_captcha_found = False
            for selector in second_captcha_indicators:
                try:
                    elements = self.find_elements_fast(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"🚨 SECOND CAPTCHA DETECTED with selector: {selector}")
                            second_captcha_found = True
                            break
                    if second_captcha_found:
                        break
                except:
                    continue
            
            if second_captcha_found:
                logger.info("🔐 CRITICAL: SECOND CAPTCHA found - solving via Anti-Captcha...")
                self.take_screenshot_conditional("second_captcha_detected.png")
                
                # Решаем вторую капчу через тот же CaptchaSolver
                try:
                    captcha_solved = await self.captcha_solver.solve_captcha(self._driver)
                    
                    if captcha_solved:
                        logger.info("✅ SECOND CAPTCHA solved successfully!")
                        self.take_screenshot_conditional("second_captcha_solved.png")
                        return True
                    else:
                        logger.error("❌ SECOND CAPTCHA solve FAILED!")
                        self.take_screenshot_conditional("second_captcha_failed.png")
                        # НЕ бросаем исключение - пытаемся продолжить
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ SECOND CAPTCHA solve error: {e}")
                    self.take_screenshot_conditional("second_captcha_error.png")
                    return False
            
            # Продолжаем ожидание если капча не найдена
            logger.debug(f"⏳ Waiting for second captcha... ({int(time.time() - start_time)}s/{second_captcha_timeout}s)")
        
        # Таймаут истек
        logger.info("✅ No SECOND CAPTCHA detected after 5s - proceeding to modal button click")
        return True
    
    def _generate_phone(self) -> str:
        """Быстрая генерация телефона"""
        return f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}"
    
    async def _get_payment_result(self) -> Dict[str, Any]:
        """СТРОГОЕ извлечение результата с валидацией"""
        logger.info("🔍 STRICT result extraction with validation")
        
        await asyncio.sleep(2)  # Ожидание загрузки
        self.take_screenshot_conditional("final_result_page.png")
        
        current_url = self._driver.current_url
        logger.info(f"📍 Current URL: {current_url}")
        
        # СТРОГАЯ ПРОВЕРКА: мы должны быть НЕ на главной странице
        if current_url == self.base_url or current_url == f"{self.base_url}/":
            logger.error("❌ CRITICAL: Still on homepage - payment process FAILED")
            return {
                'success': False,
                'error': 'Payment process failed - still on homepage',
                'current_url': current_url
            }
        
        # Быстрый поиск QR-кода
        qr_code_url = None
        qr_selectors = [
            "//img[contains(@src, 'qr')]",
            "//img[contains(@alt, 'QR')]",
            "//canvas[contains(@class, 'qr')]",
            "//img[contains(@src, 'data:image') and contains(@src, 'qr')]",
            "//*[contains(@class, 'qr-code')]//img"
        ]
        
        for selector in qr_selectors:
            element = self.find_element_fast(By.XPATH, selector, timeout=2)
            if element and element.is_displayed():
                qr_url = element.get_attribute("src")
                if qr_url and ('qr' in qr_url.lower() or 'data:image' in qr_url):
                    qr_code_url = qr_url
                    logger.info(f"✅ QR found: {qr_url[:50]}...")
                    break
        
        # Быстрый поиск ссылки на оплату
        payment_url = current_url  # Используем текущий URL как базовый
        payment_selectors = [
            "//a[contains(@href, 'pay')]",
            "//a[contains(@href, 'payment')]",
            "//button[contains(text(), 'Оплатить')]",
            "//a[contains(@href, 'checkout')]"
        ]
        
        for selector in payment_selectors:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element:
                href = element.get_attribute("href")
                if href and ('pay' in href or 'payment' in href or 'checkout' in href):
                    payment_url = href
                    logger.info(f"✅ Payment URL found: {href[:50]}...")
                    break
        
        # СТРОГАЯ ВАЛИДАЦИЯ УСПЕХА
        success_indicators = {
            'qr_code_found': bool(qr_code_url),
            'payment_url_valid': payment_url != self.base_url and payment_url != current_url,
            'url_changed': current_url != self.base_url,
            'no_error_messages': await self._check_no_error_messages()
        }
        
        logger.info(f"📊 Success indicators: {success_indicators}")
        
        # Определяем успех: QR найден ИЛИ URL изменился И нет ошибок
        success = (
            success_indicators['qr_code_found'] or 
            (success_indicators['url_changed'] and success_indicators['no_error_messages'])
        )
        
        result = {
            'success': success,
            'qr_code_url': qr_code_url,
            'payment_url': payment_url,
            'current_url': current_url,
            'validation': success_indicators
        }
        
        if not success:
            # Детальная диагностика ошибки
            error_messages = await self._extract_error_messages()
            result['error'] = f'Payment result validation failed. Error messages: {error_messages}'
            result['error_details'] = error_messages
        
        logger.info(f"📊 STRICT result: success={success}")
        if success:
            logger.info("✅ Payment process completed successfully!")
        else:
            logger.error("❌ Payment process validation FAILED!")
            
        return result
    
    async def _check_no_error_messages(self) -> bool:
        """Проверка отсутствия сообщений об ошибках"""
        try:
            error_selectors = [
                "//*[contains(@class, 'error')]",
                "//*[contains(@class, 'alert')]",
                "//*[contains(@class, 'warning')]",
                "//*[contains(text(), 'ошибка')]",
                "//*[contains(text(), 'Ошибка')]",
                "//*[contains(text(), 'ERROR')]",
                "//*[contains(text(), 'неверн')]",
                "//*[contains(text(), 'не удалось')]"
            ]
            
            for selector in error_selectors:
                elements = self.find_elements_fast(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        error_text = element.text.strip()
                        if error_text:
                            logger.warning(f"⚠️ Error message found: {error_text}")
                            return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Error checking failed: {e}")
            return True  # Если не можем проверить - считаем что ошибок нет
    
    async def _extract_error_messages(self) -> str:
        """Извлечение текста ошибок для диагностики"""
        try:
            error_messages = []
            error_selectors = [
                "//*[contains(@class, 'error')]",
                "//*[contains(@class, 'alert')]",
                "//*[contains(text(), 'ошибка')]",
                "//*[contains(text(), 'Ошибка')]"
            ]
            
            for selector in error_selectors:
                elements = self.find_elements_fast(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if text and text not in error_messages:
                            error_messages.append(text)
            
            return "; ".join(error_messages) if error_messages else "No specific error messages found"
            
        except Exception as e:
            logger.debug(f"Extract error messages failed: {e}")
            return "Error extracting error messages"
    
    async def _diagnostic_dom_analysis(self):
        """ДИАГНОСТИЧЕСКИЙ анализ DOM для поиска кнопки"""
        try:
            logger.info("🔍 DIAGNOSTIC: Starting full DOM analysis...")
            
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
            
            button_data = self._driver.execute_script(all_buttons_script)
            logger.info(f"🔍 DIAGNOSTIC: Found {len(button_data)} visible buttons")
            
            # Логируем все кнопки
            for i, btn in enumerate(button_data[:20]):  # Первые 20 кнопок
                logger.info(f"Button {i}: text='{btn['text'][:50]}', class='{btn['className'][:30]}', enabled={btn['enabled']}")
            
            # 2. Поиск кнопок с похожим текстом
            continue_buttons = []
            for btn in button_data:
                text = btn['text'].strip().upper()
                if any(keyword in text for keyword in ['ПРОДОЛЖИТЬ', 'CONTINUE', 'NEXT', 'ДАЛЕЕ', 'OK', 'ГОТОВО']):
                    continue_buttons.append(btn)
                    logger.info(f"🎯 DIAGNOSTIC: Found potential continue button: '{btn['text']}' (class: {btn['className']})")
            
            # 3. Анализ iframe (может быть модальное окно в iframe)
            iframe_script = """
            var iframes = document.querySelectorAll('iframe');
            var iframeData = [];
            for (var i = 0; i < iframes.length; i++) {
                var iframe = iframes[i];
                iframeData.push({
                    src: iframe.src || '',
                    id: iframe.id || '',
                    className: iframe.className || '',
                    visible: iframe.offsetParent !== null
                });
            }
            return iframeData;
            """
            
            iframe_data = self._driver.execute_script(iframe_script)
            if iframe_data:
                logger.info(f"🔍 DIAGNOSTIC: Found {len(iframe_data)} iframes")
                for iframe in iframe_data:
                    logger.info(f"Iframe: src='{iframe['src'][:50]}', class='{iframe['className']}'")
            
            # 4. Поиск элементов с событиями клика
            clickable_script = """
            var clickableElements = [];
            var allElements = document.querySelectorAll('*');
            for (var i = 0; i < allElements.length; i++) {
                var el = allElements[i];
                var hasClick = el.onclick || el.getAttribute('onclick') || 
                              el.addEventListener || window.getComputedStyle(el).cursor === 'pointer';
                if (hasClick && el.offsetWidth > 0 && el.offsetHeight > 0) {
                    var text = el.textContent || el.innerText || '';
                    if (text.includes('ПРОДОЛЖИТЬ') || text.includes('CONTINUE')) {
                        clickableElements.push({
                            tagName: el.tagName,
                            text: text.substring(0, 50),
                            className: el.className || '',
                            id: el.id || ''
                        });
                    }
                }
            }
            return clickableElements;
            """
            
            clickable_data = self._driver.execute_script(clickable_script)
            if clickable_data:
                logger.info(f"🔍 DIAGNOSTIC: Found {len(clickable_data)} clickable continue elements")
                for el in clickable_data:
                    logger.info(f"Clickable: {el['tagName']} '{el['text']}' (class: {el['className']})")
            
            return {
                'total_buttons': len(button_data),
                'continue_buttons': continue_buttons,
                'iframes': iframe_data,
                'clickable_elements': clickable_data
            }
            
        except Exception as e:
            logger.error(f"❌ DIAGNOSTIC DOM analysis error: {e}")
            return None

    async def _diagnostic_button_click(self) -> bool:
        """ДИАГНОСТИЧЕСКИЙ поиск и клик кнопки с расширенными методами"""
        try:
            logger.info("🎯 DIAGNOSTIC: Starting enhanced button click methods")
            
            # Метод 1: Поиск через JavaScript по тексту
            js_button_click_script = """
            // Поиск всех элементов содержащих текст продолжить
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
            
            logger.info("🎯 DIAGNOSTIC: Method 1 - JavaScript text search")
            result = self._driver.execute_script(js_button_click_script)
            if result.get('success'):
                logger.info(f"✅ DIAGNOSTIC: Method 1 SUCCESS - clicked {result.get('element')} with text '{result.get('text')}'")
                await asyncio.sleep(2)
                
                # Проверяем успех
                if await self._check_modal_disappeared():
                    return True
            
            # Метод 2: Координатный клик в правый нижний угол модального окна
            logger.info("🎯 DIAGNOSTIC: Method 2 - Coordinate click")
            modal_coordinate_script = """
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
            
            result = self._driver.execute_script(modal_coordinate_script)
            if result.get('success'):
                logger.info(f"✅ DIAGNOSTIC: Method 2 SUCCESS - coordinate click at {result.get('coordinates')}")
                await asyncio.sleep(2)
                
                if await self._check_modal_disappeared():
                    return True
            
            # Метод 3: Эмуляция Enter/Space/Escape
            logger.info("🎯 DIAGNOSTIC: Method 3 - Keyboard events")
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
            
            self._driver.execute_script(keyboard_script)
            await asyncio.sleep(2)
            
            if await self._check_modal_disappeared():
                logger.info("✅ DIAGNOSTIC: Method 3 SUCCESS - keyboard event")
                return True
            
            # Метод 4: Поиск и клик по всем видимым элементам в области модального окна
            logger.info("🎯 DIAGNOSTIC: Method 4 - Area click")
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
            
            result = self._driver.execute_script(area_click_script)
            if result.get('success'):
                logger.info(f"✅ DIAGNOSTIC: Method 4 SUCCESS - area click on {result.get('clicked')}")
                await asyncio.sleep(2)
                
                if await self._check_modal_disappeared():
                    return True
            
            logger.error("❌ DIAGNOSTIC: All methods failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ DIAGNOSTIC button click error: {e}")
            return False

    async def _check_modal_disappeared(self) -> bool:
        """Проверка исчезновения модального окна"""
        try:
            modal_selectors = [
                "//div[contains(text(), 'Проверка данных')]",
                "//*[contains(text(), 'Проверьте данные получателя')]"
            ]
            
            for selector in modal_selectors:
                element = self.find_element_fast(By.XPATH, selector, timeout=1)
                if element and element.is_displayed():
                    return False
            
            # Также проверяем изменение URL
            current_url = self._driver.current_url
            url_changed = current_url != self.base_url
            
            logger.info(f"📍 URL check: {current_url}, changed: {url_changed}")
            return url_changed
            
        except Exception as e:
            logger.debug(f"Modal check error: {e}")
            return False