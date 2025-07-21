"""
OPTIMIZED MultiTransfer.ru Browser Automation
Оптимизированная автоматизация для быстрой работы (цель: до 30 секунд)
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
    """ОПТИМИЗИРОВАННАЯ автоматизация multitransfer.ru - скорость до 30 секунд"""
    
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
        """ОПТИМИЗИРОВАННОЕ создание платежа (цель: до 30 секунд)"""
        start_time = time.time()
        try:
            logger.info(f"🚀 FAST payment creation: {payment_data['amount']} {payment_data.get('currency_from', 'RUB')}")
            
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
            await self._fast_handle_modal()
            
            # Извлечение результата
            result = await self._get_payment_result()
            
            total_time = time.time() - start_time
            logger.info(f"✅ FAST payment completed in {total_time:.1f}s!")
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
        """БЫСТРАЯ отправка и решение капчи 10-11 (цель: до 35 секунд с капчей)"""
        logger.info("🏃‍♂️ Fast submit and captcha steps 10-11")
        
        # Шаг 10: Финальная отправка
        buttons = self.find_elements_fast(By.TAG_NAME, "button")
        for btn in buttons:
            if "ПРОДОЛЖИТЬ" in (btn.text or "").upper():
                if self.click_element_fast(btn):
                    logger.info("✅ Step 10: Final form submitted")
                    break
        
        await asyncio.sleep(1)  # Ожидание обработки
        
        # Шаг 11: КРИТИЧЕСКОЕ решение капчи
        logger.info("🔐 Step 11: CRITICAL CAPTCHA solving")
        captcha_solved = await self.captcha_solver.solve_captcha(self._driver)
        
        if captcha_solved:
            logger.info("✅ Step 11: CAPTCHA solved successfully")
        else:
            logger.error("❌ Step 11: CAPTCHA solve FAILED - cannot proceed")
            # КРИТИЧЕСКОЕ: если капча не решена - СТОП
            raise Exception("CAPTCHA solve failed - payment process cannot continue")
        
        self.take_screenshot_conditional("fast_captcha_step.png")
    
    async def _fast_handle_modal(self):
        """БЫСТРАЯ обработка модального окна Step 12"""
        logger.info("🏃‍♂️ Fast modal handling step 12")
        
        await asyncio.sleep(0.5)  # Минимальное ожидание модального окна
        
        # Быстрый поиск модального окна
        modal_found = False
        for selector in self.selectors['data_verification_modal']:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element and element.is_displayed():
                modal_found = True
                break
        
        if not modal_found:
            logger.info("ℹ️ No modal found, continuing...")
            return
        
        logger.info("✅ Modal found, clicking continue...")
        
        # Быстрый клик по кнопке в модальном окне
        for selector in self.selectors['modal_continue_btn']:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element and element.is_displayed():
                if self.click_element_fast(element):
                    logger.info("✅ Step 12: Modal continue clicked")
                    break
        
        await asyncio.sleep(0.5)
        self.take_screenshot_conditional("fast_modal_handled.png")
    
    def _generate_phone(self) -> str:
        """Быстрая генерация телефона"""
        return f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}"
    
    async def _get_payment_result(self) -> Dict[str, Any]:
        """БЫСТРОЕ извлечение результата"""
        logger.info("🔍 Fast result extraction")
        
        await asyncio.sleep(1)  # Минимальное ожидание загрузки
        self.take_screenshot_conditional("fast_final_result.png")
        
        current_url = self._driver.current_url
        
        # Быстрый поиск QR-кода
        qr_code_url = None
        qr_selectors = [
            "//img[contains(@src, 'qr')]",
            "//img[contains(@alt, 'QR')]"
        ]
        
        for selector in qr_selectors:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element:
                qr_url = element.get_attribute("src")
                if qr_url:
                    qr_code_url = qr_url
                    logger.info(f"✅ QR found: {qr_url[:50]}...")
                    break
        
        # Быстрый поиск ссылки на оплату
        payment_url = current_url
        payment_selectors = [
            "//a[contains(@href, 'pay')]",
            "//button[contains(text(), 'Оплатить')]"
        ]
        
        for selector in payment_selectors:
            element = self.find_element_fast(By.XPATH, selector, timeout=1)
            if element:
                href = element.get_attribute("href")
                if href:
                    payment_url = href
                    break
        
        success = bool(qr_code_url or payment_url != self.base_url)
        
        result = {
            'success': success,
            'qr_code_url': qr_code_url,
            'payment_url': payment_url,
            'current_url': current_url
        }
        
        if not success:
            result['error'] = 'No QR code or payment URL found'
        
        logger.info(f"📊 FAST result: success={success}")
        return result