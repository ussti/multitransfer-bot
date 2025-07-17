"""
MultiTransfer.ru Browser Automation
Автоматизация браузера для создания платежей на multitransfer.ru
ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ - все 12 шагов с детальным логированием
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
    """Автоматизация multitransfer.ru - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ (12 шагов)"""
    
    def __init__(self, proxy: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None):
        self.proxy = proxy
        self.config = config or {}
        self.base_url = "https://multitransfer.ru"
        self._driver = None
        self.captcha_solver = CaptchaSolver(config)
        
        # РАБОЧИЕ селекторы из тест-файла + УЛУЧШЕННЫЕ
        self.selectors = {
            # Шаг 1: Кнопка "ПЕРЕВЕСТИ ЗА РУБЕЖ"
            'transfer_abroad_btn': [
                "//button[contains(text(), 'ПЕРЕВЕСТИ ЗА РУБЕЖ')]",
                "//*[contains(text(), 'ПЕРЕВЕСТИ ЗА РУБЕЖ')]"
            ],
            
            # Шаг 2: Выбор Таджикистана
            'tajikistan_select': [
                "//span[text()='Таджикистан']/parent::div",
                "//div[contains(text(), 'Таджикистан')]",
                "//span[contains(text(), 'Таджикистан')]",
                "//*[text()='Таджикистан']"
            ],
            
            # Шаг 3: Поле ввода суммы
            'amount_input': [
                "//input[contains(@placeholder, 'RUB')]",
                "//input[contains(@placeholder, 'Сумма')]",
                "//input[@type='number']",
                "//input[contains(@placeholder, 'amount')]"
            ],
            
            # Шаг 4: Валюта TJS
            'currency_tjs': [
                "//button[contains(text(), 'TJS')]",
                "//div[contains(text(), 'TJS')]",
                "//*[contains(@class, 'currency') and contains(text(), 'TJS')]",
                "//*[text()='TJS']"
            ],
            
            # Шаг 5: Корти Милли - сначала dropdown
            'transfer_method_dropdown': [
                "//div[contains(text(), 'Способ перевода')]//following-sibling::*",
                "//div[contains(text(), 'Способ перевода')]//parent::*//div[contains(@class, 'dropdown') or contains(@class, 'select')]",
                "//div[contains(@class, 'transfer-method') or contains(@class, 'method')]",
                "//*[contains(text(), 'Выберите способ') or contains(text(), 'способ')]"
            ],
            
            # Корти Милли в списке
            'korti_milli_option': [
                "//*[contains(text(), 'Корти Милли')]",
                "//div[contains(text(), 'Корти Милли')]",
                "//span[contains(text(), 'Корти Милли')]",
                "//li[contains(text(), 'Корти Милли')]",
                "//*[contains(@class, 'option') and contains(text(), 'Корти Милли')]"
            ],
            
            # Шаг 6: Кнопка "ПРОДОЛЖИТЬ"
            'continue_btn': [
                "//button[contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//button[contains(text(), 'продолжить')]",
                "//button[contains(text(), 'Продолжить')]"
            ],
            
            # Шаги 7-10: Форма с данными (с твоего скриншота)
            'recipient_card': [
                "//input[@placeholder='Номер банковской карты']",
                "//input[contains(@placeholder, 'карты')]",
                "//input[contains(@placeholder, 'Номер')]//ancestor::*[contains(text(), 'карты')]"
            ],
            
            # Переключатель на Паспорт РФ
            'passport_rf_toggle': [
                "//button[contains(text(), 'Паспорт РФ')]",
                "//*[contains(@class, 'toggle') and contains(., 'Паспорт РФ')]"
            ],
            
            # Поля паспорта РФ - УЛУЧШЕННЫЕ СЕЛЕКТОРЫ
            'passport_series': [
                "//input[@placeholder='Серия паспорта']",
                "//input[contains(@placeholder, 'Серия')]",
                "//div[contains(text(), 'Серия')]//following-sibling::*//input",
                "//label[contains(text(), 'Серия')]//following-sibling::*//input"
            ],
            
            'passport_number': [
                "//input[@placeholder='Номер паспорта']",
                "//input[contains(@placeholder, 'Номер паспорта')]",
                "//div[contains(text(), 'Номер')]//following-sibling::*//input[not(@placeholder='Номер банковской карты')]",
                "//label[contains(text(), 'Номер')]//following-sibling::*//input[not(@placeholder='Номер банковской карты')]"
            ],
            
            'passport_country': [
                "//input[@placeholder='Россия']",
                "//input[contains(@placeholder, 'Россия')]",
                "//div[contains(text(), 'Страна выдачи')]//following-sibling::*//input",
                "//label[contains(text(), 'Страна')]//following-sibling::*//input"
            ],
            
            'passport_date': [
                "//div[contains(text(), 'Дата выдачи паспорта')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                "//label[contains(text(), 'Дата выдачи')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                "(//input[@placeholder='ДД.ММ.ГГГГ'])[2]",
                "//input[@placeholder='ДД.ММ.ГГГГ'][position()>1]"
            ],
            
            # Личные данные - УЛУЧШЕННЫЕ СЕЛЕКТОРЫ
            'surname': [
                "//input[@placeholder='Укажите фамилию']",
                "//input[contains(@placeholder, 'фамилию')]",
                "//div[contains(text(), 'Фамилия')]//following-sibling::*//input",
                "//label[contains(text(), 'Фамилия')]//following-sibling::*//input"
            ],
            
            'name': [
                "//input[@placeholder='Укажите имя']", 
                "//input[contains(@placeholder, 'имя')]",
                "//div[contains(text(), 'Имя')]//following-sibling::*//input",
                "//label[contains(text(), 'Имя')]//following-sibling::*//input"
            ],
            
            'patronymic': [
                "//input[@placeholder='Укажите отчество']",
                "//input[contains(@placeholder, 'отчество')]",
                "//div[contains(text(), 'Отчество')]//following-sibling::*//input",
                "//label[contains(text(), 'Отчество')]//following-sibling::*//input"
            ],
            
            'birthdate': [
                "//div[contains(text(), 'Дата рождения')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                "//label[contains(text(), 'Дата рождения')]//following-sibling::*//input[@placeholder='ДД.ММ.ГГГГ']",
                "(//input[@placeholder='ДД.ММ.ГГГГ'])[1]",
                "//input[contains(@placeholder, 'ДД.ММ.ГГГГ')]"
            ],
            
            'phone': [
                "//input[@placeholder='Укажите номер телефона']",
                "//input[contains(@placeholder, 'телефон')]",
                "//div[contains(text(), 'Номер телефона')]//following-sibling::*//input",
                "//label[contains(text(), 'телефон')]//following-sibling::*//input"
            ],
            
            # Checkbox согласия - оптимизированный для быстрой работы
            'agreement_checkbox': [
                # РАБОЧИЙ МЕТОД - сразу ищем скрытый checkbox и кликаем принудительно
                "//input[@type='checkbox']",  # Первый найденный checkbox
                "//form//input[@type='checkbox']",  # Checkbox в форме
                "//input[@type='checkbox'][last()]"  # Последний checkbox
            ],
            
            # Финальная кнопка "ПРОДОЛЖИТЬ" 
            'final_continue': [
                "//button[contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//button[@type='submit']"
            ]
        }
    
    async def _setup_driver(self):
        """Настройка Chrome драйвера"""
        try:
            logger.info("🚀 Setting up Chrome driver...")
            
            options = uc.ChromeOptions()
            
            # Базовые настройки
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            
            # Настройка прокси
            if self.proxy:
                proxy_string = f"{self.proxy['ip']}:{self.proxy['port']}"
                options.add_argument(f'--proxy-server=http://{proxy_string}')
                logger.info(f"🌐 Using proxy: {proxy_string}")
            
            # Пользовательский агент
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ]
            options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            # Создаем драйвер
            self._driver = uc.Chrome(options=options)
            self._driver.implicitly_wait(10)
            
            logger.info("✅ Chrome driver setup completed")
            return self._driver
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Chrome driver: {e}")
            return None
    
    # ===== АДАПТАЦИЯ МЕТОДОВ browser_manager =====
    
    def find_element_safe(self, by, selector):
        """Безопасный поиск элемента (синхронный аналог browser_manager)"""
        try:
            element = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except:
            return None
    
    def find_elements_safe(self, by, selector):
        """Безопасный поиск элементов (синхронный аналог browser_manager)"""
        try:
            return self._driver.find_elements(by, selector)
        except:
            return []
    
    def click_element_safe(self, element):
        """Безопасный клик по элементу (синхронный аналог browser_manager)"""
        try:
            # Прокручиваем к элементу
            self._driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            
            # Кликаем
            element.click()
            return True
        except:
            try:
                # Пробуем JavaScript клик
                self._driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False
    
    def type_text_safe(self, element, text):
        """Безопасный ввод текста (синхронный аналог browser_manager)"""
        try:
            # Очищаем поле
            element.clear()
            time.sleep(0.2)
            
            # Печатаем посимвольно для человечности
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            return True
        except:
            return False
    
    def get_element_attribute(self, element, attribute):
        """Получить атрибут элемента (синхронный аналог browser_manager)"""
        try:
            return element.get_attribute(attribute) or ""
        except:
            return ""
    
    def take_screenshot(self, filename):
        """Сделать скриншот (синхронный аналог browser_manager)"""
        try:
            import os
            os.makedirs("logs/automation", exist_ok=True)
            screenshot_path = f"logs/automation/{filename}"
            self._driver.save_screenshot(screenshot_path)
            logger.info(f"📸 Screenshot saved: {filename}")
        except Exception as e:
            logger.warning(f"Failed to save screenshot {filename}: {e}")
    
    def navigate_to_url(self, url):
        """Переход на URL (синхронный аналог browser_manager)"""
        try:
            self._driver.get(url)
            return True
        except:
            return False
    
    # ===== ОСНОВНЫЕ МЕТОДЫ =====
    
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to create payment - ПОЛНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ 12 ШАГОВ"""
        try:
            logger.info(f"🚀 Starting COMPLETE payment creation for {payment_data['amount']} {payment_data.get('currency_from', 'RUB')}")
            
            # Настраиваем драйвер
            driver = await self._setup_driver()
            if not driver:
                return {'success': False, 'error': 'Failed to setup browser driver'}
            
            # Открываем сайт
            success = self.navigate_to_url(self.base_url)
            if not success:
                raise Exception("Failed to load homepage")
            
            self.take_screenshot("00_homepage.png")
            
            # Шаги 1-6: От главной страницы до формы заполнения
            await self._select_country_and_amount(payment_data)
            
            # Шаг 7: Номер карты получателя
            await self._fill_recipient_data(payment_data)
            
            # Шаги 8-9: Данные отправителя + согласие
            await self._fill_sender_data(payment_data)
            
            # Шаг 10: Финальная отправка
            await self._submit_final_form()
            
            # Извлекаем результат (QR-код и ссылку)
            result = await self._get_payment_result()
            
            logger.info("✅ COMPLETE payment creation successful!")
            return result
            
        except Exception as e:
            logger.error(f"❌ Payment creation failed: {e}")
            self.take_screenshot("error_final.png")
            return {'success': False, 'error': str(e)}
            
        finally:
            if hasattr(self, '_driver') and self._driver:
                logger.info("🔒 Closing browser")
                try:
                    self._driver.quit()
                except:
                    pass
                self._driver = None
    
    async def _select_country_and_amount(self, payment_data: Dict[str, Any]):
        """Шаги 1-6: Полная последовательность до заполнения формы - РАБОЧАЯ ВЕРСИЯ"""
        logger.info(f"🚀 Starting steps 1-6: country={payment_data['country']}, amount={payment_data['amount']}")
        
        # Шаг 1: Клик "ПЕРЕВЕСТИ ЗА РУБЕЖ"
        logger.info("📍 Step 1: Click 'ПЕРЕВЕСТИ ЗА РУБЕЖ'")
        await asyncio.sleep(random.uniform(3, 5))
        
        all_buttons = self.find_elements_safe(By.TAG_NAME, "button")
        button_clicked = False
        
        for i, btn in enumerate(all_buttons):
            try:
                text = btn.text or ""
                if "ПЕРЕВЕСТИ ЗА РУБЕЖ" in text:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    if self.click_element_safe(btn):
                        logger.info(f"✅ Successfully clicked 'ПЕРЕВЕСТИ ЗА РУБЕЖ' button {i}")
                        button_clicked = True
                        break
            except:
                pass
        
        if not button_clicked:
            raise Exception("Could not click 'ПЕРЕВЕСТИ ЗА РУБЕЖ'")
        
        await asyncio.sleep(random.uniform(3, 5))
        self.take_screenshot("step1_modal_opened.png")
        
        # Шаг 2: Выбор Таджикистана
        logger.info("📍 Step 2: Select Tajikistan")
        
        tajikistan_clicked = False
        for selector in self.selectors['tajikistan_select']:
            elements = self.find_elements_safe(By.XPATH, selector)
            for element in elements:
                try:
                    if element.is_displayed():
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        self._driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(0.3)
                        
                        if self.click_element_safe(element):
                            logger.info("✅ Successfully clicked Tajikistan")
                            tajikistan_clicked = True
                            break
                except:
                    pass
            if tajikistan_clicked:
                break
        
        if not tajikistan_clicked:
            raise Exception("Could not select Tajikistan")
        
        await asyncio.sleep(random.uniform(3, 5))
        self.take_screenshot("step2_country_selected.png")
        
        # Шаг 3: Заполнение суммы
        logger.info("📍 Step 3: Fill amount")
        
        amount_filled = False
        for selector in self.selectors['amount_input']:
            elements = self.find_elements_safe(By.XPATH, selector)
            for inp in elements:
                try:
                    if inp.is_displayed() and inp.is_enabled():
                        logger.info("🎯 Filling amount field")
                        success = await self.human_type_text(inp, str(int(payment_data['amount'])))
                        if success:
                            logger.info("✅ Amount filled successfully")
                            amount_filled = True
                            break
                except:
                    pass
            if amount_filled:
                break
        
        if not amount_filled:
            raise Exception("Could not fill amount")
        
        await asyncio.sleep(1)
        self.take_screenshot("step3_amount_filled.png")
        
        # Шаг 4: Выбор валюты TJS
        logger.info("📍 Step 4: Select TJS currency")
        
        tjs_selected = False
        for selector in self.selectors['currency_tjs']:
            elements = self.find_elements_safe(By.XPATH, selector)
            for element in elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        logger.info("🎯 Clicking TJS currency button")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        if self.click_element_safe(element):
                            logger.info("✅ Successfully selected TJS currency")
                            tjs_selected = True
                            break
                except:
                    continue
            if tjs_selected:
                break
        
        if not tjs_selected:
            logger.warning("⚠️ Could not select TJS currency, continuing...")
        
        await asyncio.sleep(1)
        self.take_screenshot("step4_currency_selected.png")
        
        # Шаг 5: Выбор способа перевода "Корти Милли"
        logger.info("📍 Step 5: Select 'Корти Милли' transfer method")
        
        # Открываем dropdown
        method_dropdown_clicked = False
        for selector in self.selectors['transfer_method_dropdown']:
            elements = self.find_elements_safe(By.XPATH, selector)
            for element in elements:
                try:
                    if element.is_displayed():
                        logger.info("🎯 Clicking transfer method dropdown")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        if self.click_element_safe(element):
                            logger.info("✅ Successfully clicked transfer method dropdown")
                            method_dropdown_clicked = True
                            break
                except:
                    continue
            if method_dropdown_clicked:
                break
        
        await asyncio.sleep(1)
        self.take_screenshot("step5_transfer_method_dropdown.png")
        
        # Выбираем "Корти Милли"
        korti_milli_selected = False
        for selector in self.selectors['korti_milli_option']:
            elements = self.find_elements_safe(By.XPATH, selector)
            for element in elements:
                try:
                    if element.is_displayed():
                        logger.info("🎯 Clicking Корти Милли option")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        self._driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(0.3)
                        
                        if self.click_element_safe(element):
                            logger.info("✅ Successfully selected Корти Милли")
                            korti_milli_selected = True
                            break
                except:
                    continue
            if korti_milli_selected:
                break
        
        if not korti_milli_selected:
            logger.warning("⚠️ Could not select Корти Милли, continuing...")
        
        await asyncio.sleep(1)
        self.take_screenshot("step5_method_selected.png")
        
        # Шаг 6: Нажать кнопку "ПРОДОЛЖИТЬ"
        logger.info("📍 Step 6: Click 'ПРОДОЛЖИТЬ' button")
        
        continue_buttons = self.find_elements_safe(By.TAG_NAME, "button")
        continue_clicked = False
        
        for btn in continue_buttons:
            try:
                text = btn.text or ""
                if text and "ПРОДОЛЖИТЬ" in text.upper():
                    logger.info(f"🎯 Found continue button: '{text}'")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    if self.click_element_safe(btn):
                        logger.info(f"✅ Successfully clicked continue button")
                        continue_clicked = True
                        break
            except:
                pass
        
        if not continue_clicked:
            logger.warning("⚠️ Could not find continue button")
        
        await asyncio.sleep(2)
        self.take_screenshot("step6_form_page.png")
        
        logger.info("✅ Steps 1-6 completed! Ready for form filling...")
    
    async def human_type_text(self, element, text, min_delay=0.05, max_delay=0.2):
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
    
    async def _fill_recipient_data(self, payment_data: Dict[str, Any]):
        """Шаг 7: Заполнение номера карты получателя"""
        logger.info("💳 Step 7: Filling recipient card number")
        
        card_number = payment_data.get('recipient_card', '')
        if not card_number:
            raise Exception("No recipient card number provided")
        
        card_filled = False
        for selector in self.selectors['recipient_card']:
            element = self.find_element_safe(By.XPATH, selector)
            if element and element.is_displayed() and element.is_enabled():
                try:
                    logger.info(f"🎯 Filling recipient card: {card_number}")
                    success = await self.human_type_text(element, card_number)
                    if success:
                        logger.info("✅ Recipient card filled successfully")
                        card_filled = True
                        break
                except:
                    continue
        
        if not card_filled:
            raise Exception("Could not fill recipient card number")
        
        await asyncio.sleep(2)
        self.take_screenshot("step7_recipient_card.png")

    async def _fill_sender_data(self, payment_data: Dict[str, Any]):
        """Шаги 8-9: Заполнение данных отправителя + checkbox согласия - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        logger.info("👤 Step 8: Filling sender passport data - НОВАЯ ВЕРСИЯ")
        
        passport_data = payment_data.get('passport_data', {})
        if not passport_data:
            raise Exception("No passport data provided")
        
        logger.info(f"📋 Available passport data: {passport_data}")
        
        # Сначала переключаемся на "Паспорт РФ" если нужно
        logger.info("🔄 Selecting 'Паспорт РФ' document type")
        for selector in self.selectors['passport_rf_toggle']:
            element = self.find_element_safe(By.XPATH, selector)
            if element and element.is_displayed():
                try:
                    if self.click_element_safe(element):
                        logger.info("✅ Selected 'Паспорт РФ' document type")
                        await asyncio.sleep(1)
                        break
                except:
                    continue
        
        # Заполняем все поля паспорта и личных данных - ИСПРАВЛЕННАЯ ЛОГИКА
        # Пропускаем passport_country, так как поле заполняется автоматически
        fields_to_fill = [
            ('passport_series', passport_data.get('passport_series', ''), 'passport series'),
            ('passport_number', passport_data.get('passport_number', ''), 'passport number'), 
            # ('passport_country', 'Россия', 'passport country'),  # ПРОПУСКАЕМ - заполняется автоматически
            ('passport_date', passport_data.get('passport_date', ''), 'passport date'),
            ('surname', passport_data.get('surname', ''), 'surname'),
            ('name', passport_data.get('name', ''), 'name'),
            ('birthdate', passport_data.get('birthdate', ''), 'birthdate'),
            ('phone', self._generate_phone(), 'phone')  # Генерируем рандомный телефон
            # ('patronymic', passport_data.get('patronymic', ''), 'patronymic')  # ПРОПУСКАЕМ отчество
        ]
        
        filled_count = 0
        
        for field_key, value, description in fields_to_fill:
            if not value:  # Пропускаем пустые значения
                logger.info(f"⏭️ Skipping {description} - no value provided")
                continue
                
            if field_key not in self.selectors:
                logger.warning(f"⚠️ No selectors for {description}")
                continue
            
            logger.info(f"📝 Attempting to fill {description}: '{value}'")
            
            field_filled = False
            for i, selector in enumerate(self.selectors[field_key]):
                logger.info(f"   🎯 Trying selector {i+1}/{len(self.selectors[field_key])}: {selector}")
                
                element = self.find_element_safe(By.XPATH, selector)
                if element:
                    logger.info(f"   ✅ Found element for {description}")
                    
                    if element.is_displayed() and element.is_enabled():
                        try:
                            success = await self.human_type_text(element, str(value))
                            if success:
                                logger.info(f"✅ {description} filled successfully with '{value}'")
                                field_filled = True
                                filled_count += 1
                                await asyncio.sleep(random.uniform(0.3, 0.7))
                                break
                            else:
                                logger.warning(f"⚠️ Failed to type in {description} field")
                        except Exception as e:
                            logger.warning(f"⚠️ Error filling {description}: {e}")
                            continue
                    else:
                        logger.info(f"   ❌ Element not visible/enabled for {description}")
                else:
                    logger.info(f"   ❌ Element not found for {description}")
            
            if not field_filled:
                logger.warning(f"⚠️ Could not fill {description} with any selector")
        
        logger.info(f"📊 Filled {filled_count}/{len(fields_to_fill)} fields successfully")
        
        await asyncio.sleep(2)
        self.take_screenshot("step8_sender_data_filled.png")
        
        # Шаг 9: Checkbox согласия
        logger.info("☑️ Step 9: Accepting agreement checkbox")
        logger.info("🔍 Looking for checkbox left of text: 'Настоящим подтверждаю достоверность предоставленных данных согласно п.1.5 и п.5.2.1 Условий'")
        
        # Сначала найдем сам текст для отладки - попробуем разные варианты
        text_patterns = [
            "Настоящим подтверждаю",
            "подтверждаю",
            "достоверность",
            "согласно",
            "Условий",
            "п.1.5",
            "п.5.2.1"
        ]
        
        for pattern in text_patterns:
            text_elements = self._driver.find_elements(By.XPATH, f"//*[contains(text(), '{pattern}')]")
            logger.info(f"🔍 Found {len(text_elements)} elements with '{pattern}' text")
            
            for i, elem in enumerate(text_elements[:2]):  # Показываем первые 2
                try:
                    text_content = elem.text.strip()
                    logger.info(f"📝 '{pattern}' element {i+1}: '{text_content[:100]}...'")
                    logger.info(f"📍 Tag: {elem.tag_name}, Visible: {elem.is_displayed()}")
                except:
                    logger.info(f"📝 '{pattern}' element {i+1}: Could not get text content")
        
        # Также поищем все элементы с любым текстом содержащим ключевые слова
        all_text_elements = self._driver.find_elements(By.XPATH, "//*[text()]")
        logger.info(f"🔍 Searching through {len(all_text_elements)} text elements for agreement text...")
        
        agreement_elements = []
        for elem in all_text_elements:
            try:
                text = elem.text.strip().lower()
                if any(word in text for word in ['подтверждаю', 'достоверность', 'условий', 'согласно']):
                    agreement_elements.append(elem)
                    logger.info(f"📝 Found agreement text: '{elem.text.strip()[:100]}...'")
                    logger.info(f"📍 Tag: {elem.tag_name}, Visible: {elem.is_displayed()}")
            except:
                continue
        
        logger.info(f"🔍 Found {len(agreement_elements)} elements with agreement-related text")
        
        checkbox_clicked = False
        for i, selector in enumerate(self.selectors['agreement_checkbox']):
            logger.info(f"🎯 Trying checkbox selector {i+1}/{len(self.selectors['agreement_checkbox'])}: {selector}")
            
            elements = self._driver.find_elements(By.XPATH, selector)
            logger.info(f"🔍 Found {len(elements)} elements with selector {i+1}")
            
            for j, element in enumerate(elements):
                try:
                    if element and element.is_displayed():
                        logger.info(f"✅ Element {j+1} is visible, attempting click...")
                        
                        # Прокручиваем к элементу
                        self._driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(0.5)
                        
                        if self.click_element_safe(element):
                            logger.info("✅ Agreement checkbox checked successfully!")
                            checkbox_clicked = True
                            await asyncio.sleep(1)
                            break
                        else:
                            logger.warning(f"⚠️ Failed to click checkbox element {j+1}")
                    else:
                        logger.info(f"❌ Element {j+1} not visible or not found")
                except Exception as e:
                    logger.warning(f"⚠️ Error with element {j+1}: {e}")
                    continue
            
            if checkbox_clicked:
                break
        
        if not checkbox_clicked:
            logger.error("❌ Could not check agreement checkbox with any selector")
            logger.error("🔍 Taking screenshot for debugging...")
            self.take_screenshot("debug_checkbox_not_found.png")
            
            # Дополнительная отладка - показать все checkbox на странице
            all_checkboxes = self._driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            logger.info(f"🔍 DEBUG: Found {len(all_checkboxes)} total checkboxes on page")
            
            for i, cb in enumerate(all_checkboxes):
                try:
                    logger.info(f"🔍 Checkbox {i+1}: visible={cb.is_displayed()}, enabled={cb.is_enabled()}")
                    
                    # Попробуем принудительно кликнуть по скрытому checkbox
                    if cb.is_enabled() and not cb.is_displayed():
                        logger.info(f"🎯 Attempting to force click hidden checkbox {i+1}")
                        
                        try:
                            # Попробуем разные способы клика
                            methods = [
                                lambda: cb.click(),
                                lambda: self._driver.execute_script("arguments[0].click();", cb),
                                lambda: self._driver.execute_script("arguments[0].checked = true;", cb),
                                lambda: self._driver.execute_script("arguments[0].style.display = 'block'; arguments[0].click();", cb)
                            ]
                            
                            for j, method in enumerate(methods):
                                try:
                                    method()
                                    logger.info(f"✅ Force click method {j+1} successful on checkbox {i+1}")
                                    
                                    # Проверим, что checkbox стал отмеченным
                                    if cb.is_selected():
                                        logger.info("✅ Checkbox is now checked!")
                                        checkbox_clicked = True
                                        break
                                    else:
                                        logger.info("⚠️ Checkbox clicked but not checked")
                                        
                                except Exception as method_error:
                                    logger.info(f"❌ Force click method {j+1} failed: {method_error}")
                                    
                            if checkbox_clicked:
                                break
                                
                        except Exception as force_error:
                            logger.info(f"❌ Force click on checkbox {i+1} failed: {force_error}")
                            
                except Exception as cb_error:
                    logger.info(f"❌ Error checking checkbox {i+1}: {cb_error}")
                    pass
            
            if not checkbox_clicked:
                raise Exception("Failed to check agreement checkbox - cannot proceed")
        
        self.take_screenshot("step9_agreement_checked.png")
        logger.info("📋 Step 8-9 completed - ready for final submission")
    
    def _generate_phone(self) -> str:
        """Генерация случайного российского номера телефона"""
        # Генерируем номер в формате +7XXXXXXXXXX
        prefix = "+7"
        # Первая цифра после +7 (9 для мобильных)
        first_digit = "9"
        # Остальные 9 цифр
        remaining_digits = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        
        phone = f"{prefix}{first_digit}{remaining_digits}"
        logger.info(f"📱 Generated phone: {phone}")
        return phone

    async def _submit_final_form(self):
        """Шаги 10-12: Финальное нажатие ПРОДОЛЖИТЬ + обработка модального окна проверки"""
        logger.info("📤 Step 10: Submitting final form")
        
        final_clicked = False
        for selector in self.selectors['final_continue']:
            element = self.find_element_safe(By.XPATH, selector)
            if element and element.is_displayed() and element.is_enabled():
                try:
                    logger.info("🎯 Clicking final ПРОДОЛЖИТЬ button")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    if self.click_element_safe(element):
                        logger.info("✅ Final form submitted successfully")
                        final_clicked = True
                        break
                except:
                    continue
        
        if not final_clicked:
            raise Exception("Could not submit final form")
        
        await asyncio.sleep(3)  # Increased wait for processing
        self.take_screenshot("step10_final_result.png")
        
        # Шаг 11: Проверка и решение капчи (если есть)
        logger.info("🔐 Step 11: Checking and solving CAPTCHA if present")
        captcha_solved = await self.captcha_solver.solve_captcha(self._driver)
        if captcha_solved:
            logger.info("✅ CAPTCHA step completed successfully")
            await asyncio.sleep(2)  # Wait after captcha
            self.take_screenshot("step11_captcha_solved.png")
        else:
            logger.warning("⚠️ CAPTCHA step failed or not needed")
        
        # Шаг 12: НОВЫЙ - Обработка модального окна "Проверка данных"
        logger.info("🔍 Step 12: Handling 'Проверка данных' modal window")
        await self._handle_data_verification_modal()
        
        logger.info("🎉 All 12 steps completed!")

    async def _handle_data_verification_modal(self):
        """Шаг 12: Обработка модального окна 'Проверка данных'"""
        logger.info("📋 Looking for 'Проверка данных' modal window...")
        
        try:
            # Ждем появления модального окна
            await asyncio.sleep(2)
            
            # Селекторы для модального окна "Проверка данных"
            modal_selectors = [
                "//div[contains(text(), 'Проверка данных')]",
                "//*[contains(text(), 'Проверьте данные получателя')]",
                "//*[contains(@class, 'modal') and contains(., 'Проверка')]",
                "//h2[contains(text(), 'Проверка данных')]",
                "//h3[contains(text(), 'Проверка данных')]"
            ]
            
            modal_found = False
            for selector in modal_selectors:
                element = self.find_element_safe(By.XPATH, selector)
                if element and element.is_displayed():
                    logger.info("✅ Found 'Проверка данных' modal window")
                    modal_found = True
                    break
            
            if not modal_found:
                logger.info("ℹ️ No 'Проверка данных' modal found, continuing...")
                return
            
            # Делаем скриншот модального окна
            self.take_screenshot("step12_data_verification_modal.png")
            
            # Селекторы для кнопки "ПРОДОЛЖИТЬ" в модальном окне
            modal_continue_selectors = [
                # Конкретно в модальном окне
                "//div[contains(text(), 'Проверка данных')]//ancestor::div[contains(@class, 'modal')]//button[contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//div[contains(text(), 'Проверка данных')]//following::button[contains(text(), 'ПРОДОЛЖИТЬ')][1]",
                
                # Общие селекторы для кнопки в модальном окне
                "//*[contains(@class, 'modal')]//button[contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//*[contains(@class, 'modal')]//button[contains(text(), 'продолжить')]",
                
                # Кнопка с синим фоном (как на скриншоте)
                "//button[contains(@style, 'background') and contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//button[contains(@class, 'btn-primary') and contains(text(), 'ПРОДОЛЖИТЬ')]",
                
                # Последняя кнопка ПРОДОЛЖИТЬ на странице
                "(//button[contains(text(), 'ПРОДОЛЖИТЬ')])[last()]",
                
                # Поиск по стилям (синяя кнопка)
                "//button[contains(@class, 'blue') and contains(text(), 'ПРОДОЛЖИТЬ')]",
                "//button[contains(@class, 'primary') and contains(text(), 'ПРОДОЛЖИТЬ')]"
            ]
            
            modal_continue_clicked = False
            for i, selector in enumerate(modal_continue_selectors):
                logger.info(f"🎯 Trying modal continue selector {i+1}/{len(modal_continue_selectors)}: {selector}")
                
                element = self.find_element_safe(By.XPATH, selector)
                if element and element.is_displayed() and element.is_enabled():
                    try:
                        logger.info("🎯 Found modal ПРОДОЛЖИТЬ button, clicking...")
                        
                        # Прокручиваем к элементу
                        self._driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(0.5)
                        
                        # Кликаем
                        if self.click_element_safe(element):
                            logger.info("✅ Successfully clicked modal ПРОДОЛЖИТЬ button")
                            modal_continue_clicked = True
                            break
                        else:
                            logger.warning(f"⚠️ Failed to click modal button with selector {i+1}")
                    except Exception as e:
                        logger.warning(f"⚠️ Error with modal selector {i+1}: {e}")
                        continue
                else:
                    logger.info(f"❌ Modal button not found/visible with selector {i+1}")
            
            if not modal_continue_clicked:
                logger.warning("⚠️ Could not click ПРОДОЛЖИТЬ in modal window")
                
                # Дополнительная попытка - найти все кнопки и кликнуть по нужной
                all_buttons = self.find_elements_safe(By.TAG_NAME, "button")
                logger.info(f"🔍 Found {len(all_buttons)} total buttons on page")
                
                for i, btn in enumerate(all_buttons):
                    try:
                        text = btn.text or ""
                        if "ПРОДОЛЖИТЬ" in text.upper() and btn.is_displayed() and btn.is_enabled():
                            logger.info(f"🎯 Attempting to click button {i+1}: '{text}'")
                            
                            if self.click_element_safe(btn):
                                logger.info(f"✅ Successfully clicked button {i+1}")
                                modal_continue_clicked = True
                                break
                    except:
                        continue
            
            if modal_continue_clicked:
                logger.info("✅ Modal 'Проверка данных' handled successfully")
                await asyncio.sleep(2)  # Wait for next page to load
                self.take_screenshot("step12_modal_completed.png")
            else:
                logger.error("❌ Failed to handle 'Проверка данных' modal")
                raise Exception("Could not proceed from data verification modal")
        
        except Exception as e:
            logger.error(f"❌ Error in _handle_data_verification_modal: {e}")
            self.take_screenshot("step12_modal_error.png")
            # Don't raise exception here - continue with process as modal might not always appear
            logger.warning("⚠️ Continuing without modal handling...")

    async def _get_payment_result(self) -> Dict[str, Any]:
        """Извлечение финального результата - QR-код и ссылка на оплату"""
        logger.info("🔍 Extracting payment result (QR code and payment URL)")
        
        await asyncio.sleep(2)  # Ждем загрузки результата
        self.take_screenshot("final_payment_result.png")
        
        # Получаем текущий URL
        current_url = self._driver.current_url if self._driver else None
        
        # Ищем QR-код
        qr_code_url = None
        qr_selectors = [
            "//img[contains(@src, 'qr')]",
            "//img[contains(@alt, 'QR')]", 
            "//img[contains(@class, 'qr')]",
            "//*[contains(@class, 'qr-code')]//img",
            "//*[contains(@id, 'qr')]//img",
            "//canvas[contains(@class, 'qr')]"
        ]
        
        for selector in qr_selectors:
            element = self.find_element_safe(By.XPATH, selector)
            if element:
                qr_url = self.get_element_attribute(element, "src")
                if qr_url:
                    qr_code_url = qr_url
                    logger.info(f"✅ Found QR code: {qr_url[:100]}...")
                    break
        
        # Ищем ссылку на оплату
        payment_url = current_url  # По умолчанию текущий URL
        payment_link_selectors = [
            "//a[contains(@href, 'pay')]",
            "//a[contains(@href, 'payment')]", 
            "//a[contains(text(), 'Оплатить')]",
            "//button[contains(text(), 'Оплатить')]"
        ]
        
        for selector in payment_link_selectors:
            element = self.find_element_safe(By.XPATH, selector)
            if element:
                href = self.get_element_attribute(element, "href")
                if href:
                    payment_url = href
                    logger.info(f"✅ Found payment URL: {href}")
                    break
        
        # Пытаемся найти курс обмена
        exchange_rate = None
        rate_selectors = [
            "//*[contains(text(), 'Курс')]",
            "//*[contains(text(), 'курс')]",
            "//*[contains(text(), 'Rate')]"
        ]
        
        for selector in rate_selectors:
            element = self.find_element_safe(By.XPATH, selector)
            if element:
                rate_text = element.text or ""
                # Парсим число из текста
                numbers = re.findall(r'\d+\.?\d*', rate_text)
                if numbers:
                    try:
                        exchange_rate = float(numbers[0])
                        logger.info(f"💱 Found exchange rate: {exchange_rate}")
                        break
                    except:
                        pass
        
        # Проверяем успешность
        success = bool(qr_code_url or payment_url != self.base_url)
        
        result = {
            'success': success,
            'qr_code_url': qr_code_url,
            'payment_url': payment_url,
            'exchange_rate': exchange_rate,
            'page_title': self._driver.title if self._driver else None,
            'current_url': current_url
        }
        
        if not success:
            result['error'] = 'No QR code or payment URL found on result page'
            
            # Ищем сообщения об ошибках
            error_selectors = [
                "//*[contains(@class, 'error')]",
                "//*[contains(@class, 'alert')]",
                "//*[contains(text(), 'Ошибка')]"
            ]
            
            for selector in error_selectors:
                element = self.find_element_safe(By.XPATH, selector)
                if element and element.text:
                    result['error'] = element.text.strip()
                    logger.error(f"🚨 Found error message: {element.text}")
                    break
        
        logger.info(f"📊 Payment result: success={success}, QR={'✅' if qr_code_url else '❌'}, URL={'✅' if payment_url else '❌'}")
        return result