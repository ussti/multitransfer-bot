"""
OPTIMIZED MultiTransfer.ru Browser Automation with SECOND CAPTCHA support
Оптимизированная автоматизация с поддержкой ВТОРОЙ КАПЧИ (50% случаев)
"""

import logging
import asyncio
import random
import time
import re
import os
import tempfile
import zipfile
import json
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from web.captcha.solver import CaptchaSolver
from .system_proxy_helper import system_proxy_manager

logger = logging.getLogger(__name__)

class MultiTransferAutomation:
    """ИСПРАВЛЕННАЯ автоматизация multitransfer.ru с поддержкой ВТОРОЙ КАПЧИ"""
    
    def __init__(self, proxy: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None, proxy_manager=None):
        self.proxy = proxy
        self.config = config or {}
        self.base_url = "https://multitransfer.ru"
        self._driver = None
        self.captcha_solver = CaptchaSolver(config)
        self.proxy_manager = proxy_manager
        
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
                "//*[text()='TJS']"  # ОПТИМИЗИРОВАНО: только рабочий селектор
            ],
            
            'transfer_method_dropdown': [
                "//*[contains(text(), 'Выберите способ') or contains(text(), 'способ')]"  # ОПТИМИЗИРОВАНО: только рабочий селектор
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
            
            # РАБОЧИЙ ПОДХОД: Chrome Extension для обхода диалогов
            extension_path = None
            if self.proxy and self.proxy.get('user') and self.proxy.get('pass'):
                logger.info("🔧 Creating Chrome Extension for proxy auth...")
                try:
                    extension_path = self._create_proxy_auth_extension(
                        self.proxy['user'], 
                        self.proxy['pass']
                    )
                    logger.info("✅ Proxy auth extension created")
                except Exception as e:
                    logger.error(f"❌ Failed to create proxy extension: {e}")
                    self.proxy = None
            
            options = uc.ChromeOptions()
            
            # DEBUG MODE START - Проверяем режим отладки
            debug_mode = os.getenv('DEBUG_BROWSER', 'false').lower() == 'true'
            visual_debug = debug_mode
            
            if visual_debug:
                # РЕЖИМ ОТЛАДКИ - браузер будет видимым и полнофункциональным
                logger.info("🔍 DEBUG MODE: Browser will be visible for debugging")
                options.add_argument('--window-size=1400,1000')
                options.add_argument('--start-maximized')
                # Добавляем флаги для стабильности в визуальном режиме
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage') 
                options.add_argument('--disable-blink-features=AutomationControlled')
                # НЕ добавляем --disable-web-security здесь - будет добавлен в PROXY режиме
                # Включаем все для лучшей отладки - изображения, JS, расширения
                logger.info("🎨 DEBUG: Enabling images, JavaScript and extensions for better debugging")
            else:
                # ПРОДАКШЕН РЕЖИМ - оптимизированные настройки для скорости
                logger.info("⚡ PRODUCTION MODE: Optimized settings for speed")
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                # КРИТИЧНО: Отключаем детекцию автоматизации (рекомендация Proxy6)
                options.add_argument('--disable-blink-features=AutomationControlled')
                # ИСПРАВЛЕНО: НЕ используем постоянный профиль - он кэширует авторизацию прокси
                # temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
                # options.add_argument(f'--user-data-dir={temp_profile}')
                options.add_argument('--incognito')  # Всегда свежая сессия
                logger.info("🔧 PROXY MODE: Using incognito mode for fresh proxy auth")
                # НЕ отключаем extensions при использовании прокси (нужны для аутентификации)
                if not self.proxy:
                    options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-images')  # Отключаем загрузку изображений
                # ИСПРАВЛЕНО: ВСЕГДА включаем JavaScript для загрузки банков
                # if not self.proxy:
                #     options.add_argument('--disable-javascript')
                logger.info("🔧 PROXY MODE: JavaScript enabled for dynamic content loading")
                options.add_argument('--window-size=1920,1080')
            # DEBUG MODE END
            
            # ТОЧНАЯ КОПИЯ ЛОГИКИ ИЗ BrowserManager
            if self.proxy:
                proxy_type = self.proxy.get('type', 'http')
                
                # Настройка прокси сервера (как в BrowserManager)
                if proxy_type == 'http':
                    options.add_argument(f"--proxy-server=http://{self.proxy['ip']}:{self.proxy['port']}")
                else:
                    options.add_argument(f"--proxy-server=socks5://{self.proxy['ip']}:{self.proxy['port']}")
                
                # Добавляем extension для аутентификации (как в BrowserManager)
                if extension_path:
                    options.add_argument(f"--load-extension={extension_path}")
                    logger.info(f"✅ Proxy auth extension loaded: {extension_path}")
                    
                logger.info(f"🔧 Using {proxy_type.upper()} proxy: {self.proxy['ip']}:{self.proxy['port']} (with extension auth)")
                
                if self.proxy.get('provider') == 'ssh_tunnel':
                    logger.info("✅ SSH tunnel proxy configured - no Chrome auth dialogs expected")
                else:
                    logger.info("✅ Chrome Extension proxy configured - no Chrome auth dialogs expected")
            
            # Быстрый user agent
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
            
            # УБРАНЫ ВСЕ ЛИШНИЕ ФЛАГИ - используем только базовые как в BrowserManager
            
            # Создаем драйвер с улучшенными настройками
            logger.info("🚀 Creating Chrome driver with Proxy6 optimizations")
            
            self._driver = uc.Chrome(options=options)
            
            # Адаптивные таймауты в зависимости от использования прокси (увеличены после рекомендаций Proxy6)
            if self.proxy:
                self._driver.implicitly_wait(20)  # Увеличено для стабильности прокси на macOS
                self._driver.set_page_load_timeout(120)  # Увеличено для Chrome extension auth на macOS+VPN
                logger.info("⏱️ PROXY MODE: Extended timeouts for macOS stability (20s implicit, 120s page load)")
                # Дополнительная задержка для инициализации расширения
                await asyncio.sleep(3)
                logger.info("⏳ PROXY MODE: Extension initialization delay completed")
            else:
                self._driver.implicitly_wait(3)   # Быстро без прокси
                self._driver.set_page_load_timeout(30)  # 30 сек без прокси
                logger.info("⚡ DIRECT MODE: Fast timeouts enabled (3s implicit, 30s page load)")
            
            # Дополнительная задержка для стабильности в визуальном режиме
            if visual_debug:
                logger.info("⏱️ DEBUG MODE: Adding extra delay for browser stability")
                await asyncio.sleep(2)
            
            # ИСПРАВЛЕНО: Простая проверка встроенной прокси авторизации  
            if self.proxy:
                logger.info("🔐 PROXY MODE: Testing built-in proxy authentication...")
                
                # Короткая задержка для инициализации
                await asyncio.sleep(3)
                
                # Быстрый тест прокси
                try:
                    logger.info("🌐 PROXY TEST: Quick multitransfer.ru test...")
                    self._driver.get("https://multitransfer.ru")
                    await asyncio.sleep(5)
                    
                    page_length = len(self._driver.page_source)
                    logger.info(f"🔍 PROXY TEST: Content length={page_length}")
                    
                    if page_length < 1000:
                        # Для современных прокси (SOCKS5 и HTTP с URL-авторизацией) диалог не нужен
                        if self.proxy.get('type', 'http').lower() in ['socks5', 'http']:
                            logger.warning("⚠️ Proxy auth failed - proxy may be blocked or invalid")
                            logger.warning(f"⚠️ Proxy type: {self.proxy.get('type', 'unknown')}, IP: {self.proxy.get('ip', 'unknown')}")
                        else:
                            # Только для других типов пробуем диалог
                            logger.warning("⚠️ Unknown proxy type - checking for dialog...")
                            await self._handle_proxy_auth_dialog()
                            await asyncio.sleep(3)
                            
                            # Повторная проверка
                            page_length = len(self._driver.page_source)
                            logger.info(f"🔍 PROXY TEST: After manual auth length={page_length}")
                    
                    # Возвращаемся для штатного процесса
                    self._driver.get("about:blank")
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ PROXY TEST: Failed: {e}")
                    # Пробуем обработать диалог как fallback
                    await self._handle_proxy_auth_dialog()
            
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
    
    async def monitor_verification_modal(self):
        """НЕПРЕРЫВНЫЙ мониторинг модального окна 'Проверка данных' - может появиться в любой момент"""
        try:
            # Быстрая проверка на наличие модального окна
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
                    # ИСПРАВЛЕНО: Используем быстрый поиск с timeout=1 секунда
                    element = self.find_element_fast(By.XPATH, selector, timeout=1)
                    if element and element.is_displayed():
                        logger.warning("🚨 URGENT: 'Проверка данных' modal detected during operation!")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Modal monitoring error: {e}")
            return False
    
    async def handle_verification_modal_if_present(self):
        """Обработка модального окна 'Проверка данных' если оно обнаружено"""
        try:
            modal_detected = await self.monitor_verification_modal()
            if modal_detected:
                logger.info("🚨 HANDLING: 'Проверка данных' modal found - processing immediately")
                
                # Делаем скриншот
                self.take_screenshot_conditional("urgent_modal_detected.png")
                
                # Вызываем полную обработку модального окна
                await self._fast_handle_modal_with_second_captcha()
                
                logger.info("✅ HANDLED: 'Проверка данных' modal processed")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error handling verification modal: {e}")
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
    
    def take_debug_screenshot(self, filename: str, force: bool = False):
        """DEBUG скриншот для разработки"""
        import os
        from datetime import datetime
        
        debug_enabled = os.getenv('DEBUG_SCREENSHOTS', 'false').lower() == 'true'
        
        if not force and not debug_enabled:
            return
        
        if not self._driver:
            return
            
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            debug_filename = f"{timestamp}_{filename}"
            
            os.makedirs("logs/automation/debug_screenshots", exist_ok=True)
            
            screenshot_path = f"logs/automation/debug_screenshots/{debug_filename}"
            self._driver.save_screenshot(screenshot_path)
            logger.info(f"🐛 DEBUG Screenshot: {screenshot_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save debug screenshot: {e}")
    
    def _create_proxy_auth_extension(self, username: str, password: str) -> str:
        """
        Создает Chrome extension для автоматической авторизации прокси
        
        Args:
            username: Имя пользователя прокси
            password: Пароль прокси
            
        Returns:
            Путь к созданному расширению (.crx файлу)
        """
        try:
            logger.info(f"🔧 Creating proxy auth extension for user: {username}")
            
            # Создаем постоянную папку для extension (рабочая версия из BrowserManager)
            extension_dir = os.path.join(os.getcwd(), 'proxy_auth_extension')
            os.makedirs(extension_dir, exist_ok=True)
            
            # Manifest файл для Chrome extension
            manifest = {
                "version": "1.0.0",
                "manifest_version": 2,
                "name": "Chrome Proxy Auth",
                "permissions": [
                    "proxy",
                    "tabs",
                    "unlimitedStorage",
                    "storage",
                    "<all_urls>",
                    "webRequest",
                    "webRequestBlocking"
                ],
                "background": {
                    "scripts": ["background.js"]
                },
                "minimum_chrome_version": "22.0.0"
            }
            
            # Улучшенный Background script для стабильной авторизации (рекомендации Proxy6)
            background_js = f"""
console.log('Proxy6 Auth Extension: Starting');

var config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "http",
            host: "{self.proxy['ip']}",
            port: parseInt("{self.proxy['port']}")
        }},
        bypassList: ["localhost", "127.0.0.1", "::1"]
    }}
}};

// Настройка прокси с обработкой ошибок
chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{
    if (chrome.runtime.lastError) {{
        console.error('Proxy6 Auth Extension: Error setting proxy:', chrome.runtime.lastError);
    }} else {{
        console.log('Proxy6 Auth Extension: Proxy configured successfully');
    }}
}});

// Обработчик авторизации с логированием
function callbackFn(details) {{
    console.log('Proxy6 Auth Extension: Auth request for', details.url);
    return {{
        authCredentials: {{
            username: "{username}",
            password: "{password}"
        }}
    }};
}}

// Подписка на события авторизации
chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ['blocking']
);

console.log('Proxy6 Auth Extension: Ready');
"""
            
            # Сохраняем файлы extension
            with open(os.path.join(extension_dir, "manifest.json"), 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            
            with open(os.path.join(extension_dir, "background.js"), 'w', encoding='utf-8') as f:
                f.write(background_js)
            
            # Создаем .crx архив
            # НЕ создаем .crx файл, возвращаем путь к папке (как в BrowserManager)
            logger.info(f"✅ Proxy auth extension created: {extension_dir}")
            return extension_dir
            
        except Exception as e:
            logger.error(f"❌ Failed to create proxy auth extension: {e}")
            raise Exception(f"Proxy auth extension creation failed: {e}")
    
    async def _handle_proxy_auth_dialog(self):
        """
        Обработка диалога авторизации прокси Chrome
        """
        try:
            logger.info("🔍 Looking for Chrome proxy authentication dialog...")
            
            # Даем время диалогу появиться
            await asyncio.sleep(3)
            
            # Пробуем разные способы обработки диалога
            
            # Способ 1: Отправляем клавиши прямо в активное окно
            try:
                logger.info("🔤 Trying to fill auth via direct key sending...")
                
                # Нажимаем Tab чтобы убедиться что в поле username
                self._driver.switch_to.active_element.send_keys(Keys.TAB)
                await asyncio.sleep(0.5)
                
                # Очищаем и вводим username
                self._driver.switch_to.active_element.clear()
                self._driver.switch_to.active_element.send_keys(self.proxy['user'])
                await asyncio.sleep(0.5)
                
                # Переходим к полю password
                self._driver.switch_to.active_element.send_keys(Keys.TAB)
                await asyncio.sleep(0.5)
                
                # Вводим password
                self._driver.switch_to.active_element.send_keys(self.proxy['pass'])
                await asyncio.sleep(0.5)
                
                # Нажимаем Enter или ищем кнопку Sign In
                self._driver.switch_to.active_element.send_keys(Keys.ENTER)
                
                logger.info("✅ Proxy credentials sent via direct key input")
                await asyncio.sleep(2)
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Direct key method failed: {e}")
            
            # Способ 2: Попробуем alert
            try:
                alert = self._driver.switch_to.alert
                alert_text = alert.text
                logger.info(f"🔍 Found alert: {alert_text}")
                
                if "proxy" in alert_text.lower() or "username" in alert_text.lower():
                    # Для базовой HTTP аутентификации
                    credentials = f"{self.proxy['user']}:{self.proxy['pass']}"
                    alert.send_keys(credentials)
                    alert.accept()
                    logger.info("✅ Credentials sent via alert")
                    return True
                else:
                    alert.dismiss()
                    
            except Exception as e:
                logger.debug(f"No alert found: {e}")
            
            # Способ 3: Ищем в DOM (fallback)
            try:
                logger.info("🔍 Searching for auth fields in DOM...")
                username_selectors = [
                    "input[type='text']",
                    "input[placeholder*='username']",
                    "input[placeholder*='Username']",
                    "input[name='username']",
                    "#username"
                ]
                
                password_selectors = [
                    "input[type='password']",
                    "input[placeholder*='password']", 
                    "input[placeholder*='Password']",
                    "input[name='password']",
                    "#password"
                ]
                
                username_field = None
                password_field = None
                
                # Ищем поля ввода
                for selector in username_selectors:
                    try:
                        username_field = self._driver.find_element(By.CSS_SELECTOR, selector)
                        if username_field.is_displayed():
                            break
                    except:
                        continue
                
                for selector in password_selectors:
                    try:
                        password_field = self._driver.find_element(By.CSS_SELECTOR, selector)
                        if password_field.is_displayed():
                            break
                    except:
                        continue
                
                if username_field and password_field:
                    logger.info("🔍 Found proxy auth modal fields")
                    
                    # Заполняем поля
                    username_field.clear()
                    username_field.send_keys(self.proxy['user'])
                    
                    password_field.clear()
                    password_field.send_keys(self.proxy['pass'])
                    
                    # Ищем кнопку отправки
                    submit_selectors = [
                        "button[type='submit']",
                        "input[type='submit']",
                        "button:contains('Sign In')",
                        "button:contains('OK')",
                        "button:contains('Login')"
                    ]
                    
                    submit_button = None
                    for selector in submit_selectors:
                        try:
                            submit_button = self._driver.find_element(By.CSS_SELECTOR, selector)
                            if submit_button.is_displayed():
                                break
                        except:
                            continue
                    
                    if submit_button:
                        submit_button.click()
                        logger.info("✅ Proxy credentials submitted via DOM")
                        return True
                    else:
                        # Fallback: нажимаем Enter
                        password_field.send_keys(Keys.ENTER)
                        logger.info("✅ Proxy credentials submitted via Enter")
                        return True
                        
                else:
                    logger.warning("⚠️ No auth fields found in DOM")
                    
            except Exception as e:
                logger.warning(f"⚠️ DOM search failed: {e}")
            
            # Если ничего не сработало
            logger.warning("⚠️ All proxy auth methods failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Proxy auth dialog handling failed: {e}")
            return False

    def check_connection_health(self) -> bool:
        """Проверить здоровье соединения с сайтом"""
        try:
            current_url = self._driver.current_url
            page_source = self._driver.page_source
            
            # Проверяем на стандартные ошибки соединения
            connection_errors = [
                "can't be reached",
                "ERR_TIMED_OUT", 
                "ERR_CONNECTION_REFUSED",
                "ERR_PROXY_CONNECTION_FAILED",
                "This site can't be reached",
                "took too long to respond",
                "No internet"
            ]
            
            for error in connection_errors:
                if error in page_source:
                    logger.error(f"❌ Connection error detected: {error}")
                    return False
            
            # Проверяем что мы на правильном сайте
            if "multitransfer" not in current_url.lower():
                logger.error(f"❌ Wrong site detected. Current URL: {current_url}")
                return False
                
            logger.debug(f"✅ Connection healthy. URL: {current_url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking connection health: {e}")
            return False
    
    async def switch_proxy_and_retry(self, operation_func, operation_name: str = "operation") -> Any:
        """Переключить прокси и повторить операцию при ошибке соединения"""
        if not self.proxy_manager:
            logger.warning("⚠️ No proxy manager available for automatic switching")
            return await operation_func()
        
        try:
            # Сначала отмечаем текущий прокси как проблемный
            old_proxy = self.proxy
            if old_proxy and self.proxy_manager:
                logger.info(f"🚫 Marking failed proxy: {old_proxy['ip']}:{old_proxy['port']}")
                await self.proxy_manager.mark_proxy_failed(old_proxy['ip'], old_proxy['port'])
            
            # Получаем новый прокси
            logger.info(f"🔄 Getting new proxy for {operation_name}")
            new_proxy = await self.proxy_manager.get_proxy()
            
            if not new_proxy:
                logger.warning("⚠️ No alternative proxy available - trying direct connection")
                # Fallback на прямое соединение
                return await self._try_direct_connection(operation_func, operation_name)
            
            # Проверяем что получили действительно новый прокси
            if old_proxy and new_proxy['ip'] == old_proxy['ip'] and new_proxy['port'] == old_proxy['port']:
                logger.warning(f"⚠️ Got same proxy again: {new_proxy['ip']}:{new_proxy['port']}")
                # Пробуем получить еще один
                new_proxy = await self.proxy_manager.get_proxy()
                if not new_proxy:
                    logger.warning("⚠️ No different proxy available - trying direct connection")
                    return await self._try_direct_connection(operation_func, operation_name)
                elif new_proxy['ip'] == old_proxy['ip'] and new_proxy['port'] == old_proxy['port']:
                    logger.warning("⚠️ Still same proxy - trying direct connection")
                    return await self._try_direct_connection(operation_func, operation_name)
            
            # Закрываем текущий браузер и восстанавливаем системные настройки прокси
            if self._driver:
                try:
                    self._driver.quit()
                except:
                    pass
                self._driver = None
            
            # Восстанавливаем системные настройки прокси
            await system_proxy_manager.restore_settings()
            
            # Обновляем прокси и запускаем новый браузер
            self.proxy = new_proxy
            logger.info(f"🌐 Switched from {old_proxy['ip'] if old_proxy else 'direct'} to {new_proxy['ip']}:{new_proxy['port']}")
            
            # Запускаем браузер с новым прокси
            await self._setup_driver()
            
            # КРИТИЧНО: Открываем сайт заново после переключения прокси
            logger.info(f"🌐 Re-opening website with new proxy: {self.base_url}")
            self._driver.get(self.base_url)
            await asyncio.sleep(2)  # Даем время на загрузку
            
            # Проверяем что сайт загрузился
            if not self.check_connection_health():
                logger.error("❌ New proxy also failed to load site - trying direct connection")
                return await self._try_direct_connection(operation_func, operation_name)
            
            logger.info("✅ Successfully switched proxy and loaded site")
            
            # Выполняем операцию с новым прокси
            result = await operation_func()
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Proxy switch failed: {e} - trying direct connection")
            return await self._try_direct_connection(operation_func, operation_name)
    
    async def _try_direct_connection(self, operation_func, operation_name: str) -> Any:
        """Fallback на прямое соединение когда все прокси не работают"""
        try:
            logger.info(f"🌐 Trying direct connection for {operation_name}")
            
            # Закрываем текущий браузер
            if self._driver:
                try:
                    self._driver.quit()
                except:
                    pass
                self._driver = None
            
            # Отключаем прокси
            old_proxy = self.proxy
            self.proxy = None
            logger.info(f"🔀 Switched from proxy {old_proxy['ip'] if old_proxy else 'unknown'} to direct connection")
            
            # Запускаем браузер без прокси
            await self._setup_driver()
            
            # Открываем сайт напрямую
            logger.info(f"🌐 Opening website directly: {self.base_url}")
            self._driver.get(self.base_url)
            await asyncio.sleep(2)  # Даем время на загрузку
            
            # Проверяем что сайт загрузился
            if not self.check_connection_health():
                logger.error("❌ Direct connection also failed")
                raise Exception("Both proxy and direct connection failed")
            
            logger.info("✅ Successfully switched to direct connection")
            
            # Выполняем операцию с прямым соединением
            result = await operation_func()
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Direct connection failed: {e}")
            raise Exception(f"All connection methods failed: {e}")
    
    async def retry_on_connection_failure(self, operation_func, max_retries: int = 2, operation_name: str = "operation"):
        """Retry операции при потере соединения с автоматическим переключением прокси"""
        for attempt in range(max_retries + 1):
            try:
                # Проверяем соединение перед попыткой
                if not self.check_connection_health():
                    if attempt < max_retries:
                        logger.warning(f"🔄 Connection unhealthy, retry {attempt + 1}/{max_retries} for {operation_name}")
                        
                        # На первой попытке пробуем обновить страницу
                        if attempt == 0:
                            await asyncio.sleep(5)  # Ждем 5 секунд
                            try:
                                self._driver.refresh()
                                await asyncio.sleep(3)
                                continue
                            except:
                                logger.warning("⚠️ Page refresh failed")
                        
                        # На второй попытке переключаем прокси если доступен
                        if attempt >= 1 and self.proxy_manager:
                            try:
                                return await self.switch_proxy_and_retry(operation_func, operation_name)
                            except Exception as switch_error:
                                logger.error(f"❌ Proxy switch failed: {switch_error}")
                                
                        await asyncio.sleep(5)
                        continue
                    else:
                        raise Exception(f"Connection failed after {max_retries} retries for {operation_name}")
                
                # Выполняем операцию
                return await operation_func()
                
            except Exception as e:
                if attempt < max_retries and ("connection" in str(e).lower() or "timeout" in str(e).lower()):
                    logger.warning(f"🔄 {operation_name} failed (attempt {attempt + 1}), retrying: {e}")
                    await asyncio.sleep(5)
                    continue
                else:
                    raise e
        
        raise Exception(f"All retry attempts failed for {operation_name}")
    
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
            
            # Открытие сайта с обработкой ошибок и автоматическим переключением прокси
            async def open_website():
                logger.info(f"🌐 Opening website: {self.base_url}")
                
                # ИСПРАВЛЕНО: Более надежный переход на сайт
                try:
                    self._driver.get(self.base_url)
                    await asyncio.sleep(2)  # Базовое время загрузки
                    
                    # Проверяем что действительно попали на сайт
                    current_url = self._driver.current_url
                    page_title = self._driver.title
                    
                    logger.info(f"📄 Current URL: {current_url}")
                    logger.info(f"📄 Page title: '{page_title}'")
                    
                    if not current_url or "about:blank" in current_url or "chrome://" in current_url:
                        logger.error("❌ Failed to navigate to website - still on blank page")
                        return False
                        
                    if "multitransfer" not in current_url.lower():
                        logger.warning(f"⚠️ Unexpected URL: {current_url}")
                    
                    logger.info("✅ Website opened successfully")
                    
                    # ИСПРАВЛЕНО: Увеличиваем задержку - прокси требует больше времени для JS
                    if self.proxy:
                        logger.info("⏳ PROXY MODE: Waiting for JavaScript and content to load...")
                        await asyncio.sleep(10)  # Увеличено с 5 до 10 секунд для полной загрузки JS
                        
                        # Дополнительная проверка что контент действительно загрузился
                        page_length = len(self._driver.page_source)
                        logger.info(f"📄 PROXY MODE: Final page content length: {page_length} bytes")
                        
                        if page_length < 1000:
                            logger.warning("⚠️ Page still looks empty, waiting more...")
                            await asyncio.sleep(5)  # Еще 5 секунд если мало контента
                    
                    self.take_screenshot_conditional("00_homepage.png")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error during website navigation: {e}")
                    return False
            
            try:
                await self.retry_on_connection_failure(open_website, max_retries=2, operation_name="opening website")
            except Exception as e:
                logger.error(f"❌ Failed to open website: {e}")
                if "target window already closed" in str(e):
                    logger.error("💡 Browser window was closed. This might be due to Chrome flags in debug mode.")
                    logger.error("🔧 Try running again - sometimes undetected_chromedriver needs a retry.")
                raise Exception(f"Failed to open website: {e}")
            
            
            # ОПТИМИЗИРОВАННАЯ последовательность
            await self._fast_country_and_amount(payment_data)
            await self._fast_fill_forms(payment_data)
            await self._fast_submit_and_captcha()
            
            # ОПТИМИЗИРОВАНО: Пропуск шагов при раннем QR успехе
            if hasattr(self, 'early_qr_success') and self.early_qr_success:
                logger.info("🚀 ОПТИМИЗАЦИЯ: Пропуск Step 12 - QR страница уже обнаружена!")
            else:
                # ИСПРАВЛЕННЫЙ Step 12: Модальное окно "Проверка данных" с ВТОРОЙ КАПЧЕЙ
                await self._fast_handle_modal_with_second_captcha()
            
            # ОПТИМИЗИРОВАНО: Пропуск Step 13 при раннем QR успехе
            if hasattr(self, 'early_qr_success') and self.early_qr_success:
                logger.info("🚀 ОПТИМИЗАЦИЯ: Пропуск Step 13 - QR страница уже обнаружена!")
            else:
                # Step 13: ФИНАЛЬНАЯ кнопка "ПРОДОЛЖИТЬ" после обработки модального окна (только если не на QR странице)
                current_url_check = self._driver.current_url
                if 'transferId=' in current_url_check and 'paymentSystemTransferNum=' in current_url_check:
                    logger.info("🎉 ПРОПУСК Step 13: Уже на финальной странице с QR!")
                else:
                    await self._final_continue_button_click()
            
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
        """БЫСТРЫЕ шаги 1-6: страна и сумма с автоматическим переключением прокси (цель: 8-10 секунд)"""
        logger.info("🏃‍♂️ Fast steps 1-6: country and amount")
        
        # ОТЛАДКА: Проверяем состояние страницы перед началом
        try:
            current_url = self._driver.current_url
            page_source_length = len(self._driver.page_source)
            buttons_count = len(self._driver.find_elements(By.TAG_NAME, "button"))
            
            logger.info(f"🔍 DEBUG: URL={current_url}")
            logger.info(f"🔍 DEBUG: Page source length={page_source_length}")
            logger.info(f"🔍 DEBUG: Buttons found={buttons_count}")
            
            if buttons_count == 0:
                logger.error("❌ CRITICAL: No buttons found on page - content may not be loaded!")
                self.take_screenshot_conditional("debug_no_buttons.png")
                
        except Exception as debug_error:
            logger.error(f"❌ DEBUG error: {debug_error}")
        
        # Выполняем шаги с автоматическим переключением прокси при ошибках соединения
        await self.retry_on_connection_failure(
            lambda: self._do_country_and_amount_steps(payment_data),
            max_retries=2,
            operation_name="country and amount selection"
        )
    
    async def _do_country_and_amount_steps(self, payment_data: Dict[str, Any]):
        """Внутренняя реализация шагов выбора страны и суммы"""
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
        
        # Проверка на модальное окно
        await self.handle_verification_modal_if_present()
        
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
        
        # DEBUG: Скриншот перед выбором банка
        self.take_debug_screenshot("bank_selection_before.png")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: здоровье соединения перед выбором банка
        if not self.check_connection_health():
            logger.error("❌ CRITICAL: Connection unhealthy before bank selection!")
            self.take_debug_screenshot("connection_failed_before_bank.png", force=True)
            raise Exception("Connection lost or unhealthy - cannot proceed with bank selection")
        
        # Выбираем Корти Милли или fallback на "Все карты"
        korti_selected = False
        for selector in self.selectors['korti_milli_option']:
            elements = self.find_elements_fast(By.XPATH, selector)
            for element in elements:
                if element.is_displayed() and self.click_element_fast(element):
                    logger.info("✅ Step 5: Korti Milli selected")
                    korti_selected = True
                    break
            if korti_selected:
                break
        
        # Fallback: если Корти Милли не найден, выбираем "Все карты"
        if not korti_selected:
            logger.warning("⚠️ Korti Milli not found, trying 'Все карты' fallback")
            
            # DEBUG: Скриншот при переходе к fallback
            self.take_debug_screenshot("korti_milli_not_found.png")
            
            fallback_selectors = [
                "//*[contains(text(), 'Все карты')]",
                "//*[contains(text(), 'ВСЕ КАРТЫ')]",
                "//button[contains(text(), 'Все карты')]",
                "//div[contains(text(), 'Все карты')]",
                "//span[contains(text(), 'Все карты')]",     # Быстрое дополнение
                "//label[contains(text(), 'Все карты')]",    # Быстрое дополнение
                "//*[contains(text(), 'Другие банки')]",     # Альтернативное название
                "//*[contains(@class, 'bank') and contains(text(), 'Все')]"
            ]
            
            for selector in fallback_selectors:
                elements = self.find_elements_fast(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and self.click_element_fast(element):
                        logger.info("✅ Step 5: 'Все карты' selected as fallback")
                        korti_selected = True
                        break
                if korti_selected:
                    break
        
        if not korti_selected:
            logger.error("❌ CRITICAL: Neither Korti Milli nor 'Все карты' could be selected")
            
            # Дополнительная проверка соединения при неудаче
            if not self.check_connection_health():
                logger.error("❌ DOUBLE CHECK: Connection lost during bank selection!")
                self.take_debug_screenshot("connection_lost_during_bank_selection.png", force=True)
                raise Exception("Connection lost during bank selection - this explains why banks were not found")
            
            # Быстрая диагностика - показываем первые 5 элементов с "карт"
            try:
                card_elements = self._driver.find_elements(By.XPATH, "//*[contains(text(), 'карт') or contains(text(), 'КАРТ')]")[:5]
                logger.error(f"🔍 Found {len(card_elements)} elements with 'карт':")
                for i, elem in enumerate(card_elements):
                    try:
                        logger.error(f"  {i+1}. '{elem.text.strip()[:30]}' (visible: {elem.is_displayed()})")
                    except:
                        pass
            except:
                pass
            
            # DEBUG: Критический скриншот при полном провале
            self.take_debug_screenshot("bank_selection_failed_critical.png", force=True)
            self.take_screenshot_conditional("bank_selection_failed.png")
            raise Exception("Bank selection failed - cannot continue without selecting a bank")
        
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
        """БЫСТРОЕ заполнение форм 7-9 с автоматическим переключением прокси (цель: 8-10 секунд)"""
        logger.info("🏃‍♂️ Fast form filling steps 7-9")
        
        # Выполняем заполнение форм с автоматическим переключением прокси при ошибках соединения
        await self.retry_on_connection_failure(
            lambda: self._do_fill_forms_steps(payment_data),
            max_retries=2,
            operation_name="form filling"
        )
    
    async def _do_fill_forms_steps(self, payment_data: Dict[str, Any]):
        """Внутренняя реализация заполнения форм"""
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
        checkbox_checked = False
        for cb in checkboxes:
            try:
                # Принудительный клик через JavaScript
                self._driver.execute_script("arguments[0].click();", cb)
                if cb.is_selected():
                    logger.info("✅ Step 9: Agreement checkbox checked")
                    checkbox_checked = True
                    break
            except:
                continue
        
        # БЫСТРАЯ ПРОВЕРКА: После клика по чекбоксу согласия может появиться модальное окно "Проверка данных"
        if checkbox_checked:
            logger.info("🚨 FAST CHECK: Quick modal check after checkbox (2s max)")
            await asyncio.sleep(0.5)  # Минимальная задержка
            
            # Быстрая проверка только 2 секунды вместо 10
            for attempt in range(2):
                modal_detected = await self.handle_verification_modal_if_present()
                if modal_detected:
                    logger.info("✅ HANDLED: Modal found and processed quickly")
                    break
                await asyncio.sleep(1)  # Проверяем 2 раза по 1 секунде
            
            logger.info("✅ FAST CHECK: Modal check completed (2s total)")
        
        self.take_screenshot_conditional("fast_forms_filled.png")
        logger.info("🏃‍♂️ Forms filled FAST!")
    
    async def _fast_submit_and_captcha(self):
        """БЫСТРАЯ отправка и решение ПЕРВОЙ капчи с автоматическим переключением прокси (цель: до 35 секунд с капчей)"""
        logger.info("🏃‍♂️ Fast submit and FIRST captcha steps 10-11")
        
        # Выполняем отправку и решение капчи с автоматическим переключением прокси при ошибках соединения
        await self.retry_on_connection_failure(
            lambda: self._do_submit_and_captcha_steps(),
            max_retries=2,
            operation_name="submit and captcha"
        )
    
    async def _do_submit_and_captcha_steps(self):
        """Внутренняя реализация отправки и решения капчи"""
        
        # Шаг 10: Финальная отправка
        buttons = self.find_elements_fast(By.TAG_NAME, "button")
        form_submitted = False
        for btn in buttons:
            if "ПРОДОЛЖИТЬ" in (btn.text or "").upper():
                if self.click_element_fast(btn):
                    logger.info("✅ Step 10: Final form submitted")
                    form_submitted = True
                    break
        
        await asyncio.sleep(1)  # Ожидание обработки
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: После отправки формы может появиться модальное окно "Проверка данных"
        if form_submitted:
            logger.info("🚨 MONITORING: Checking for 'Проверка данных' modal after form submit")
            
            # Быстрая проверка 2 секунды после отправки
            for attempt in range(2):
                modal_detected = await self.handle_verification_modal_if_present()
                if modal_detected:
                    logger.info("✅ HANDLED: Modal processed after form submit")
                    break
                await asyncio.sleep(1)
            
            logger.info("✅ MONITORING: Modal check completed after form submit")
        
        # Шаг 11: КРИТИЧЕСКОЕ решение ПЕРВОЙ капчи
        logger.info("🔐 Step 11: CRITICAL FIRST CAPTCHA solving")
        captcha_solved = await self.captcha_solver.solve_captcha(self._driver)
        
        if captcha_solved:
            logger.info("✅ Step 11: FIRST CAPTCHA solved successfully")
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: После решения первой капчи может появиться модальное окно "Проверка данных"
            logger.info("🚨 MONITORING: Checking for 'Проверка данных' modal after FIRST captcha")
            
            # Быстрая проверка 2 секунды после решения капчи
            for attempt in range(2):
                modal_detected = await self.handle_verification_modal_if_present()
                if modal_detected:
                    logger.info("✅ HANDLED: Modal processed after FIRST captcha")
                    break
                await asyncio.sleep(1)
            
            logger.info("✅ MONITORING: Modal check completed after FIRST captcha")
            
        else:
            logger.error("❌ Step 11: FIRST CAPTCHA solve FAILED - cannot proceed")
            # КРИТИЧЕСКОЕ: если капча не решена - СТОП
            raise Exception("FIRST CAPTCHA solve failed - payment process cannot continue")
        
        # ДОБАВЛЕНО: Проверка QR страницы после успешного решения первой капчи
        current_url_after_captcha = self._driver.current_url
        if 'transferId=' in current_url_after_captcha and 'paymentSystemTransferNum=' in current_url_after_captcha:
            logger.info("🎉 РАННИЙ УСПЕХ: QR страница обнаружена после Step 11 (первая капча)!")
            logger.info(f"💾 ФИНАЛЬНЫЙ URL: {current_url_after_captcha}")
            self.successful_qr_url = current_url_after_captcha
            # Устанавливаем флаг для пропуска последующих шагов
            self.early_qr_success = True
        else:
            self.early_qr_success = False
        
        self.take_screenshot_conditional("fast_first_captcha_solved.png")
    
    async def _fast_handle_modal_with_second_captcha(self):
        """
        БЫСТРАЯ обработка модального окна с 10-секундным таймаутом
        ОПТИМИЗИРОВАНО: при успешном QR завершение сценария
        """
        logger.info("🏃‍♂️ Step 12: FAST modal + SECOND CAPTCHA handling (10s timeout)")
        step12_start = time.time()
        
        # ПРОВЕРКА QR РАНЬШЕ - если уже на финальной странице, прекращаем поиск модалок
        current_url = self._driver.current_url
        if ('transferId=' in current_url and 'paymentSystemTransferNum=' in current_url):
            logger.info("🎉 ОПТИМИЗАЦИЯ: Уже на странице с QR - пропускаем Step 12!")
            logger.info(f"💾 СОХРАНЕН успешный URL для Step 14: {current_url}")
            self.successful_qr_url = current_url
            elapsed = time.time() - step12_start
            logger.info(f"✅ Step 12 completed in {elapsed:.1f}s (QR page detected early)")
            return
        
        # БЫСТРЫЙ поиск модального окна "Проверка данных" с 10-секундным лимитом
        modal_selectors = [
            "//div[contains(text(), 'Проверка данных')]",
            "//*[contains(text(), 'Проверьте данные получателя')]",
            "//*[contains(text(), 'Проверка данных')]",
            "//h2[contains(text(), 'Проверка данных')]",
            "//h3[contains(text(), 'Проверка данных')]"
        ]
        
        modal_found = False
        modal_element = None
        
        # Ищем модальное окно в течение МАКСИМУМ 3 секунд (ускорено)
        start_time = time.time()
        timeout_seconds = 3
        
        while (time.time() - start_time) < timeout_seconds:
            for selector in modal_selectors:
                element = self.find_element_fast(By.XPATH, selector, timeout=1)
                if element and element.is_displayed():
                    logger.info(f"✅ Found 'Проверка данных' modal with selector: {selector} after {time.time() - start_time:.1f}s")
                    modal_found = True
                    modal_element = element
                    break
            
            if modal_found:
                break
                
            await asyncio.sleep(0.5)  # Короткая пауза между проверками
        
        if not modal_found:
            elapsed = time.time() - step12_start
            logger.warning(f"⚠️ No 'Проверка данных' modal found after {elapsed:.1f}s - proceeding to Step 13")
            # Делаем скриншот для диагностики текущего состояния
            self.take_screenshot_conditional("no_modal_found_proceeding_step13.png")
            logger.info(f"✅ Step 12 completed in {elapsed:.1f}s (no modal)")
            return
        
        self.take_screenshot_conditional("step12_modal_found.png")
        
        # ПРОВЕРКА ВТОРОЙ КАПЧИ
        logger.info("🔍 CRITICAL: Checking for SECOND CAPTCHA (50% probability)")
        await self._handle_potential_second_captcha()
        
        # ВОССТАНОВЛЕННЫЙ ПРОСТОЙ ПОДХОД: оригинальный селектор [last()]
        logger.info("🎯 ORIGINAL: Using simple [last()] selector for modal button")
        
        # ИСПРАВЛЕННЫЕ селекторы на основе скриншота модального окна
        modal_button_selectors = [
            # Любой элемент с текстом ПРОДОЛЖИТЬ (не только button)
            "//*[contains(text(), 'ПРОДОЛЖИТЬ')]",  
            "//*[contains(text(), 'Продолжить')]",
            "//*[text()='ПРОДОЛЖИТЬ']",
            "//*[text()='Продолжить']",
            # В контексте модального окна "Проверка данных"
            "//div[contains(text(), 'Проверка данных')]/following::*[contains(text(), 'ПРОДОЛЖИТЬ')]",
            "//div[contains(text(), 'Проверьте данные получателя')]/following::*[contains(text(), 'ПРОДОЛЖИТЬ')]",
            # Кликабельные элементы с текстом ПРОДОЛЖИТЬ
            "//div[contains(text(), 'ПРОДОЛЖИТЬ') and contains(@class, 'btn')]",
            "//a[contains(text(), 'ПРОДОЛЖИТЬ')]",
            "//span[contains(text(), 'ПРОДОЛЖИТЬ')]"
        ]
        
        button_clicked = False
        for selector in modal_button_selectors:
            try:
                button = self.find_element_fast(By.XPATH, selector, timeout=2)
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
                    
                    logger.info(f"✅ FIXED: Found modal button with selector: {selector}")
                    logger.info(f"   Button text: '{button_text}', HTML: '{button_html[:50]}'")
                    
                    # Скроллим к кнопке
                    self._driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    await asyncio.sleep(0.5)
                    
                    # Кликаем простым способом
                    try:
                        button.click()
                        logger.info("✅ FIXED: Modal button clicked successfully")
                        button_clicked = True
                        break
                    except:
                        # Fallback к JavaScript клику
                        self._driver.execute_script("arguments[0].click();", button)
                        logger.info("✅ FIXED: Modal button clicked via JavaScript")
                        button_clicked = True
                        break
            except Exception as e:
                logger.debug(f"⚠️ Selector {selector} failed: {e}")
                continue
        
        if button_clicked:
            logger.info("✅ ORIGINAL SUCCESS: Modal handled with simple approach!")
            await asyncio.sleep(2)
            self.take_screenshot_conditional("step12_modal_success.png")
        else:
            logger.error("❌ ORIGINAL FAILURE: Could not find modal button")
            self.take_screenshot_conditional("step12_modal_failure.png")
            raise Exception("ORIGINAL: Failed to handle modal - payment cannot be completed")
        
        elapsed = time.time() - step12_start
        logger.info(f"✅ Step 12 completed in {elapsed:.1f}s (modal found and processed)")
    
    async def _handle_form_return_scenario(self):
        """
        Обработка сценария возврата к форме ввода данных
        Сначала проверяем на вторую капчу, потом ищем синюю кнопку "Продолжить"
        """
        logger.info("🔍 Handling form return scenario - checking for second captcha first")
        
        # Делаем скриншот текущего состояния
        self.take_screenshot_conditional("form_return_scenario.png")
        
        # Сначала проверяем на вторую капчу
        logger.info("🔍 CHECKING for potential SECOND CAPTCHA in form return scenario...")
        await self._handle_potential_second_captcha()
        
        logger.info("🔍 Now looking for blue 'Продолжить' button after captcha check")
        
        # Сначала проверяем, где мы находимся
        current_url = self._driver.current_url
        logger.info(f"📍 Current location before button search: {current_url}")
        
        # Если мы на главной странице - это означает, что процесс уже завершился неудачно
        if current_url == "https://multitransfer.ru/" or "/transfer/" not in current_url:
            logger.error("❌ Already on homepage - payment process failed earlier!")
            logger.error("💡 This means the form submission or previous steps failed")
            self.take_screenshot_conditional("already_on_homepage.png")
            raise Exception("Payment process failed - redirected to homepage before button search")
        
        # Расширенные селекторы для кнопки продолжения 
        continue_button_selectors = [
            # Стандартные варианты с "Продолжить"
            "//button[contains(text(), 'Продолжить')]",
            "//button[contains(text(), 'ПРОДОЛЖИТЬ')]", 
            "//input[@type='submit' and contains(@value, 'Продолжить')]",
            "//input[@type='submit' and contains(@value, 'ПРОДОЛЖИТЬ')]",
            "//button[contains(@class, 'btn') and contains(text(), 'Продолжить')]",
            "//button[contains(@class, 'btn-primary') and contains(text(), 'Продолжить')]",
            "//a[contains(@class, 'btn') and contains(text(), 'Продолжить')]",
            "//*[@type='submit' and contains(text(), 'Продолжить')]",
            "//*[contains(@class, 'btn') and contains(., 'Продолжить')]",
            
            # Альтернативные тексты кнопок
            "//button[contains(text(), 'Отправить')]",
            "//button[contains(text(), 'ОТПРАВИТЬ')]",
            "//button[contains(text(), 'Далее')]",
            "//button[contains(text(), 'ДАЛЕЕ')]",
            "//button[contains(text(), 'Подтвердить')]",
            "//button[contains(text(), 'ПОДТВЕРДИТЬ')]",
            "//button[contains(text(), 'Создать перевод')]",
            "//button[contains(text(), 'СОЗДАТЬ ПЕРЕВОД')]",
            "//button[contains(text(), 'Перевести')]",
            "//button[contains(text(), 'ПЕРЕВЕСТИ')]",
            
            # Submit кнопки с альтернативными текстами
            "//input[@type='submit' and contains(@value, 'Отправить')]",
            "//input[@type='submit' and contains(@value, 'Далее')]",
            "//input[@type='submit' and contains(@value, 'Подтвердить')]",
            "//input[@type='submit' and contains(@value, 'Создать')]",
            
            # Submit элементы (но НЕ с текстом Reload/Details)
            "//button[@type='submit' and not(contains(text(), 'Reload')) and not(contains(text(), 'Details'))]",
            "//input[@type='submit' and not(contains(@value, 'Reload')) and not(contains(@value, 'Details'))]",
            
            # Синие кнопки по классам (НО исключаем известные проблемные)
            "//button[contains(@class, 'btn-primary') and not(contains(text(), 'Reload')) and not(contains(text(), 'Details'))]",
            "//button[contains(@class, 'primary') and not(contains(text(), 'Reload')) and not(contains(text(), 'Details'))]",
            
            # Любые submit элементы (кроме проблемных)
            "//*[@type='submit' and not(contains(text(), 'Reload')) and not(contains(text(), 'Details'))]",
            
            # Широкий поиск по классам btn (исключая проблемные)
            "//button[contains(@class, 'btn') and not(contains(text(), 'Reload')) and not(contains(text(), 'Details'))]",
            
            # Последний шанс - любые кликабельные элементы с правильным текстом
            "//*[contains(text(), 'продолжить')]",
            "//*[contains(text(), 'отправить')]", 
            "//*[contains(text(), 'далее')]",
            "//*[contains(text(), 'подтвердить')]"
        ]
        
        button_found = False
        for i, selector in enumerate(continue_button_selectors):
            try:
                logger.debug(f"🔍 Trying selector {i+1}/{len(continue_button_selectors)}: {selector}")
                button = self.find_element_fast(By.XPATH, selector, timeout=2)
                if button and button.is_displayed():
                    button_text = button.text.strip() if hasattr(button, 'text') else ''
                    button_value = button.get_attribute('value') if button.get_attribute('value') else ''
                    button_tag = button.tag_name.lower()
                    
                    # Простая фильтрация - исключаем только явно вредные кнопки
                    bad_buttons = ['reload', 'details', 'назад', 'back', 'cancel', 'отмена', 'close', 'закрыть']
                    if (button_tag not in ['button', 'input', 'a'] or 
                        len(button_text) > 100 or  # Очень длинный текст
                        any(bad in button_text.lower() for bad in bad_buttons)):
                        logger.debug(f"   Skipping: bad button - '{button_text}'")
                        continue
                    
                    logger.info(f"✅ Found valid button with selector: {selector}")
                    logger.info(f"   Button: tag='{button_tag}', text='{button_text}', value='{button_value}'")
                    
                    # Скроллим к кнопке и кликаем
                    self._driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    await asyncio.sleep(1)
                    
                    # Пытаемся кликнуть
                    try:
                        button.click()
                        logger.info("✅ Successfully clicked button with normal click")
                        button_found = True
                        break
                    except Exception as click_error:
                        logger.warning(f"⚠️ Failed to click button with normal click: {click_error}")
                        # Попробуем JavaScript клик
                        try:
                            self._driver.execute_script("arguments[0].click();", button)
                            logger.info("✅ Successfully clicked button via JavaScript")
                            button_found = True
                            break
                        except Exception as js_error:
                            logger.warning(f"⚠️ JavaScript click also failed: {js_error}")
                            # Попробуем через ActionChains
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(self._driver).move_to_element(button).click().perform()
                                logger.info("✅ Successfully clicked button via ActionChains")
                                button_found = True
                                break
                            except Exception as action_error:
                                logger.warning(f"⚠️ ActionChains click also failed: {action_error}")
                                continue
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        if button_found:
            logger.info("✅ Button clicked - verifying page change...")
            
            # Запоминаем текущий URL перед кликом для проверки
            url_before = self._driver.current_url
            await asyncio.sleep(3)  # Ждем обработку формы
            url_after = self._driver.current_url
            
            # Проверяем изменилась ли страница или появились ли ошибки
            error_indicators = [
                "Паспорт РФ",
                "Иностранный Паспорт", 
                "Введите 4 цифры серии паспорта",
                "Дата выдачи паспорта",
                "Дата рождения"
            ]
            
            page_source = self._driver.page_source
            errors_found = [error for error in error_indicators if error in page_source]
            
            if errors_found:
                logger.error(f"❌ Click failed - page returned to form validation! Errors: {errors_found}")
                logger.error(f"📍 URL before: {url_before}")
                logger.error(f"📍 URL after: {url_after}")
                self.take_screenshot_conditional("form_return_failed_validation.png")
                
                # Возможно нужно заполнить поля заново или найти другую кнопку
                logger.warning("⚠️ Attempting to handle validation errors...")
                
                # Пробуем найти и кликнуть другие кнопки продолжения
                additional_selectors = [
                    "//button[contains(@class, 'btn-primary') and (contains(text(), 'Продолжить') or contains(text(), 'ПРОДОЛЖИТЬ'))]",
                    "//input[@type='submit' and (contains(@value, 'Продолжить') or contains(@value, 'ПРОДОЛЖИТЬ'))]",
                    "//button[@type='submit']",
                    "//*[@type='submit' and @form]"
                ]
                
                retry_success = False
                for selector in additional_selectors:
                    try:
                        retry_btn = self.find_element_fast(By.XPATH, selector, timeout=2)
                        if retry_btn and retry_btn.is_displayed():
                            logger.info(f"🔄 Trying alternative button: {selector}")
                            self._driver.execute_script("arguments[0].click();", retry_btn)
                            await asyncio.sleep(2)
                            
                            # Проверяем результат
                            new_page_source = self._driver.page_source
                            new_errors = [error for error in error_indicators if error in new_page_source]
                            if not new_errors:
                                logger.info("✅ Alternative button worked!")
                                retry_success = True
                                break
                    except:
                        continue
                
                if not retry_success:
                    logger.error("❌ All retry attempts failed - form validation errors persist")
                    raise Exception("Form return scenario failed - validation errors after button click")
            else:
                logger.info("✅ Form return scenario handled successfully - no validation errors")
                self.take_screenshot_conditional("form_return_success.png")
        else:
            logger.error("❌ Could not find any button in form return scenario")
            
            # Диагностическая информация
            try:
                # Получаем текущий URL
                current_url = self._driver.current_url
                logger.error(f"📍 Current URL: {current_url}")
                
                # Получаем заголовок страницы
                page_title = self._driver.title
                logger.error(f"📄 Page title: {page_title}")
                
                # Ищем все кнопки на странице для диагностики
                all_buttons = self._driver.find_elements(By.TAG_NAME, "button")
                logger.error(f"🔍 Found {len(all_buttons)} button elements on page")
                
                for i, btn in enumerate(all_buttons[:10]):  # Показываем первые 10 кнопок
                    try:
                        btn_text = btn.text.strip()
                        btn_class = btn.get_attribute("class")
                        btn_type = btn.get_attribute("type")
                        btn_visible = btn.is_displayed()
                        logger.error(f"  Button {i+1}: text='{btn_text}', class='{btn_class}', type='{btn_type}', visible={btn_visible}")
                    except:
                        pass
                
                # Ищем все input submit элементы
                all_inputs = self._driver.find_elements(By.XPATH, "//input[@type='submit']")
                logger.error(f"🔍 Found {len(all_inputs)} input[type='submit'] elements")
                
                for i, inp in enumerate(all_inputs[:5]):  # Показываем первые 5 инпутов
                    try:
                        inp_value = inp.get_attribute("value")
                        inp_class = inp.get_attribute("class")
                        inp_visible = inp.is_displayed()
                        logger.error(f"  Input {i+1}: value='{inp_value}', class='{inp_class}', visible={inp_visible}")
                    except:
                        pass
                        
            except Exception as diag_error:
                logger.error(f"❌ Error during diagnostic: {diag_error}")
            
            self.take_screenshot_conditional("form_return_failure.png")
            raise Exception("Failed to handle form return scenario - no suitable button found")
    
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
        """СТРОГОЕ извлечение результата с валидацией
        ОПТИМИЗИРОВАНО: использование сохраненного URL
        """
        logger.info("📍 Step 14: Extract payment result (QR code/URL)")
        
        await asyncio.sleep(2)  # Ожидание загрузки
        
        current_url = self._driver.current_url
        logger.info(f"📍 Final URL: {current_url}")
        
        # ПРИОРИТЕТ: Используем ТЕКУЩИЙ финальный URL вместо сохраненного короткого
        if 'transferId=' in current_url and 'paymentSystemTransferNum=' in current_url:
            logger.info("🎉 УСПЕХ: Финальный URL содержит transferId и paymentSystemTransferNum!")
        elif hasattr(self, 'successful_qr_url') and self.successful_qr_url and 'transferId=' in self.successful_qr_url:
            logger.info(f"💾 Fallback: Используем сохраненный URL из Step 12: {self.successful_qr_url}")
            current_url = self.successful_qr_url
            logger.info("🎉 УСПЕХ: Сохраненный URL содержит transferId и paymentSystemTransferNum!")
        else:
            logger.warning("⚠️ Ни текущий, ни сохраненный URL не содержат QR параметры")
        
        self.take_screenshot_conditional("final_result_page.png")
        
        # СТРОГАЯ ПРОВЕРКА: мы должны быть НЕ на главной странице
        if current_url == self.base_url or current_url == f"{self.base_url}/":
            logger.error("❌ CRITICAL: Still on homepage - payment process FAILED")
            return {
                'success': False,
                'error': 'Payment process failed - still on homepage',
                'current_url': current_url
            }
        
        # УЛУЧШЕННЫЙ поиск QR-кода с расширенными селекторами
        logger.info("🔍 Ищем QR код на странице...")
        qr_code_url = None
        qr_selectors = [
            # Приоритет 1: Canvas элементы (основной источник QR)
            "//canvas",
            "//canvas[contains(@class, 'qr')]",
            "//canvas[contains(@id, 'qr')]",
            
            # Приоритет 2: Base64 изображения в data URI
            "//img[starts-with(@src, 'data:image')]",
            
            # Приоритет 3: QR-специфичные селекторы
            "//img[contains(@src, 'qr')]",
            "//img[contains(@alt, 'qr')]", 
            "//img[contains(@alt, 'QR')]",
            "//img[contains(@class, 'qr')]",
            "//img[contains(@id, 'qr')]",
            
            # Приоритет 4: Контейнеры с QR
            "//*[contains(@class, 'qr')]//img",
            "//*[contains(@class, 'qr')]//canvas",
            "//*[contains(@class, 'qrcode')]//img",
            "//*[contains(@class, 'qrcode')]//canvas",
            "//*[contains(@id, 'qr')]//img",
            "//*[contains(@id, 'qr')]//canvas",
            
            # Приоритет 5: Общие изображения
            "//img[contains(@src, 'png')]",
            "//img[contains(@src, 'jpg')]",
            "//img[contains(@src, 'jpeg')]"
        ]
        
        for i, selector in enumerate(qr_selectors, 1):
            elements = self.find_elements_fast(By.XPATH, selector)
            logger.info(f"🔍 Selector {i}: {selector} - найдено {len(elements)} элементов")
            
            for element in elements:
                if not element.is_displayed():
                    continue
                    
                # Для canvas получаем QR через JS
                if element.tag_name == 'canvas':
                    try:
                        # Проверяем размер canvas (QR код должен быть не пустым)
                        canvas_info = self._driver.execute_script("""
                            var canvas = arguments[0];
                            return {
                                width: canvas.width,
                                height: canvas.height,
                                hasContent: canvas.width > 0 && canvas.height > 0
                            };
                        """, element)
                        
                        if canvas_info['hasContent'] and canvas_info['width'] >= 100:  # Минимальный размер QR
                            canvas_data = self._driver.execute_script(
                                "return arguments[0].toDataURL('image/png');", element
                            )
                            if canvas_data and canvas_data.startswith('data:image') and len(canvas_data) > 1000:  # Не пустое изображение
                                qr_code_url = canvas_data
                                logger.info(f"✅ QR код найден в CANVAS ({canvas_info['width']}x{canvas_info['height']}) и конвертирован в PNG!")
                                break
                        else:
                            logger.debug(f"⚠️ Canvas слишком маленький: {canvas_info}")
                    except Exception as e:
                        logger.debug(f"⚠️ Canvas обработка ошибка: {e}")
                        continue
                        
                # Для img получаем src
                elif element.tag_name == 'img':
                    qr_url = element.get_attribute("src")
                    if qr_url:
                        # ФИЛЬТРАЦИЯ неправильных SVG (исключаем декоративные иконки)
                        if 'svg' in qr_url and ('sun.fd' in qr_url or 'icon' in qr_url or len(qr_url) < 100):
                            logger.info(f"⚠️ Пропускаем декоративный SVG: {qr_url[:50]}...")
                            continue
                            
                        # Принимаем только правильные QR коды
                        if ('qr' in qr_url.lower() or 'data:image' in qr_url or 
                            (qr_url.startswith('http') and len(qr_url) > 50)):
                            qr_code_url = qr_url
                            logger.info(f"✅ QR код найден в IMG: {qr_url[:50]}...")
                            break
            
            if qr_code_url:
                break
                
        if not qr_code_url:
            logger.warning("⚠️ QR код не найден на странице")
        
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

    async def _final_continue_button_click(self):
        """Step 13: БЫСТРЫЙ клик по кнопке ПРОДОЛЖИТЬ без лишних задержек
        ОПТИМИЗИРОВАНО: пропуск при успешном QR
        """
        # ПРОВЕРКА QR РАНЬШЕ - если уже на финальной странице, пропускаем Step 13
        current_url = self._driver.current_url
        if ('transferId=' in current_url and 'paymentSystemTransferNum=' in current_url):
            logger.info("🎉 ОПТИМИЗАЦИЯ: Уже на странице с QR - пропускаем Step 13!")
            logger.info(f"💾 СОХРАНЕН успешный URL для Step 14: {current_url}")
            self.successful_qr_url = current_url
            return
        
        logger.info("⚡ Step 13: FAST 'ПРОДОЛЖИТЬ' button click - NO delays!")
        
        # УБИРАЕМ скриншот для скорости (только в debug режиме)
        # self.take_screenshot_conditional("13_final_page_before_continue.png")
        
        # УБИРАЕМ проверку URL - не нужна для клика
        # current_url = self._driver.current_url
        # logger.info(f"📍 Current URL before final continue: {current_url}")
        
        # УБИРАЕМ задержку 2 секунды - сразу ищем кнопку!
        # await asyncio.sleep(2)
        
        # ⚡ БЫСТРЫЙ Метод 1: JavaScript поиск и клик за один вызов (самый быстрый!)
        logger.info("⚡ Trying FASTEST method: JavaScript instant search and click")
        
        fast_js_script = """
        // УЛУЧШЕННЫЙ поиск кнопки ПРОДОЛЖИТЬ с отладкой
        var keywords = ['ПРОДОЛЖИТЬ', 'Продолжить', 'продолжить', 'CONTINUE', 'Continue'];
        var buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"], a[role="button"], div[role="button"]');
        
        console.log('FAST: Total buttons found:', buttons.length);
        
        for (var i = 0; i < buttons.length; i++) {
            var btn = buttons[i];
            var text = (btn.textContent || btn.value || btn.innerText || '').trim();
            
            // Логируем все кнопки для отладки
            if (text) {
                console.log('FAST: Button', i, 'text:', text, 'visible:', btn.offsetParent !== null, 'enabled:', !btn.disabled);
            }
            
            // Проверяем видимость и активность
            if (btn.offsetParent !== null && !btn.disabled) {
                // Точное совпадение с ключевыми словами
                for (var j = 0; j < keywords.length; j++) {
                    if (text === keywords[j] || text.includes(keywords[j])) {
                        console.log('FAST: FOUND TARGET! Clicking button:', text);
                        btn.scrollIntoView({block: 'center', behavior: 'smooth'});
                        setTimeout(function() { btn.click(); }, 100);
                        return {success: true, method: 'js_instant', text: text};
                    }
                }
            }
        }
        return {success: false};
        """
        
        try:
            result = self._driver.execute_script(fast_js_script)
            if result.get('success'):
                logger.info(f"✅ FASTEST SUCCESS: Clicked button '{result.get('text')}' via {result.get('method')}")
                # Минимальная задержка для обработки клика
                await asyncio.sleep(1)
                logger.info("✅ Step 13 completed INSTANTLY!")
                return
        except Exception as e:
            logger.warning(f"⚠️ Fast JS method failed: {e}")
        
        # ⚡ БЫСТРЫЙ Метод 2: Только самые вероятные селекторы (если JS не сработал)
        logger.info("⚡ Trying FAST method: Priority selectors only")
        
        fast_selectors = [
            "//button[contains(text(), 'ПРОДОЛЖИТЬ')]",  # Самый вероятный
            "//button[text()='ПРОДОЛЖИТЬ']",  # Точное совпадение
            "//button[contains(text(), 'Продолжить')]",  # Второй по вероятности
            "//input[@type='submit' and contains(@value, 'ПРОДОЛЖИТЬ')]",  # Submit кнопки
            "//button[contains(@class, 'btn') and contains(text(), 'ПРОДОЛЖИТЬ')]",  # С CSS классом
            "//*[@type='button' and contains(text(), 'ПРОДОЛЖИТЬ')]",  # Любой элемент типа button
            "//div[contains(@class, 'button') and contains(text(), 'ПРОДОЛЖИТЬ')]",  # Div-кнопки
        ]
        
        button_found = False
        
        # Быстрый поиск только по приоритетным селекторам
        for i, selector in enumerate(fast_selectors):
            try:
                element = self._driver.find_element(By.XPATH, selector)
                if element and element.is_displayed() and element.is_enabled():
                    logger.info(f"✅ FAST: Found button with selector #{i}")
                    
                    # Быстрый клик без задержек
                    try:
                        element.click()
                        logger.info(f"✅ FAST: Clicked via normal click")
                        button_found = True
                        break
                    except:
                        # JavaScript клик если обычный не сработал
                        self._driver.execute_script("arguments[0].click();", element)
                        logger.info(f"✅ FAST: Clicked via JavaScript")
                        button_found = True
                        break
                        
            except Exception as e:
                logger.debug(f"Selector #{i} failed: {e}")
                continue
        
        # ⚡ БЫСТРЫЙ Fallback: Только один дополнительный поиск если основные методы не сработали
        if not button_found:
            logger.info("⚡ FAST: Trying enhanced fallback search")
            
            # Расширенный JavaScript поиск с диагностикой
            enhanced_search = """
            // Ищем все возможные кнопки и логируем их для диагностики
            var allButtons = document.querySelectorAll('button, input[type="submit"], input[type="button"], a[role="button"]');
            var foundButtons = [];
            
            console.log('FAST: Total buttons found:', allButtons.length);
            
            for (var i = 0; i < allButtons.length; i++) {
                var btn = allButtons[i];
                var text = btn.textContent || btn.value || btn.innerText || '';
                var visible = btn.offsetParent !== null && !btn.disabled;
                
                // Добавляем в диагностику все видимые кнопки
                if (visible && text.trim()) {
                    foundButtons.push({
                        index: i,
                        text: text.trim(),
                        tagName: btn.tagName,
                        className: btn.className || ''
                    });
                }
                
                // Ищем кнопки продолжить (разные варианты)
                var continueKeywords = [
                    'ПРОДОЛЖИТЬ', 'Продолжить', 'продолжить',
                    'CONTINUE', 'Continue', 'continue',
                    'ДАЛЕЕ', 'Далее', 'далее',
                    'NEXT', 'Next', 'next',
                    'ОТПРАВИТЬ', 'Отправить'
                ];
                
                if (visible) {
                    for (var j = 0; j < continueKeywords.length; j++) {
                        if (text.includes(continueKeywords[j])) {
                            console.log('FAST: Found and clicking button:', text);
                            btn.scrollIntoView({block: 'center', behavior: 'instant'});
                            btn.click();
                            return {
                                success: true, 
                                text: text.trim(),
                                method: 'enhanced_fallback',
                                totalButtons: allButtons.length,
                                foundButtons: foundButtons.length
                            };
                        }
                    }
                }
            }
            
            return {
                success: false,
                totalButtons: allButtons.length,
                foundButtons: foundButtons,
                message: 'No continue button found'
            };
            """
            
            try:
                result = self._driver.execute_script(enhanced_search)
                if result.get('success'):
                    logger.info(f"✅ FAST: Enhanced fallback found button '{result.get('text')}'")
                    logger.info(f"📊 FAST: Scanned {result.get('totalButtons')} buttons, {result.get('foundButtons')} visible")
                    button_found = True
                else:
                    logger.error(f"❌ FAST: No continue button found in {result.get('totalButtons')} buttons")
                    
                    # Диагностика - показываем найденные кнопки
                    found_buttons = result.get('foundButtons', [])[:5]  # Первые 5
                    logger.error("🔍 FAST: Available buttons:")
                    for btn_info in found_buttons:
                        logger.error(f"  - '{btn_info.get('text', '')[:30]}' ({btn_info.get('tagName')})")
                        
            except Exception as e:
                logger.error(f"❌ FAST: Enhanced fallback failed: {e}")
        
        # ⚡ БЫСТРОЕ завершение
        if button_found:
            logger.info("✅ FAST: Step 13 completed successfully!")
            # Минимальная задержка для обработки клика
            await asyncio.sleep(1)
        else:
            logger.error("❌ FAST: Could not find ПРОДОЛЖИТЬ button with any method")
            # Делаем скриншот только при ошибке
            self.take_screenshot_conditional("13_fast_button_not_found.png")
            raise Exception("FAST: Final ПРОДОЛЖИТЬ button not found after all search methods")
        
        logger.info("⚡ FAST: Step 13 completed in minimal time!")

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
    
    async def cleanup(self):
        """Очистка ресурсов и восстановление системных настроек"""
        try:
            logger.info("🧹 Cleaning up MultiTransfer automation...")
            
            # Закрываем браузер
            if hasattr(self, '_driver') and self._driver:
                try:
                    self._driver.quit()
                except:
                    pass
                self._driver = None
            
            # Восстанавливаем системные настройки прокси
            await system_proxy_manager.restore_settings()
            
            # Останавливаем SSH туннели если используем proxy_manager
            if hasattr(self, 'proxy_manager') and self.proxy_manager:
                await self.proxy_manager.ssh_tunnel_manager.stop_tunnel()
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    def __del__(self):
        """Деструктор для автоматической очистки"""
        try:
            if hasattr(self, '_driver') and self._driver:
                self._driver.quit()
        except:
            pass