"""
Browser Fingerprinting Evasion Module - Скрытие automation признаков
Включает маскировку WebDriver, подмену navigator properties, stealth режим
"""

import random
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class StealthBrowser:
    """Модуль для скрытия automation признаков браузера"""
    
    # Список реальных User-Agent строк
    USER_AGENTS = [
        # Chrome на macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        
        # Chrome на Windows 10/11
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        
        # Chrome на Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    # Возможные разрешения экрана
    SCREEN_RESOLUTIONS = [
        (1920, 1080),  # Full HD
        (1366, 768),   # Popular laptop
        (1440, 900),   # MacBook Air
        (1280, 720),   # HD
        (1536, 864),   # Scaled
        (1600, 900),   # Wide
        (2560, 1440),  # 2K
    ]
    
    @staticmethod
    def get_stealth_options() -> Options:
        """
        Получить Chrome options для максимального скрытия automation
        
        Returns:
            Options: Настроенные Chrome options
        """
        logger.info("🛡️ Creating stealth Chrome options")
        
        options = Options()
        
        # === ОСНОВНЫЕ STEALTH НАСТРОЙКИ ===
        
        # Отключить automation флаги (СОВМЕСТИМО С MACOS)
        # NOTE: excludeSwitches не поддерживается в некоторых версиях undetected-chromedriver
        # options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        # options.add_experimental_option('useAutomationExtension', False)
        
        # Более совместимый подход для macOS
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-automation")
        options.add_argument("--disable-infobars")
        
        # === АНТИДЕТЕКТ ФЛАГИ ===
        
        # Отключить различные детекционные механизмы
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-field-trial-config")
        options.add_argument("--disable-back-forward-cache")
        options.add_argument("--disable-ipc-flooding-protection")
        
        # Отключить дополнительные функции детекции
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-prompt-on-repost")
        options.add_argument("--disable-domain-reliability")
        options.add_argument("--disable-component-extensions-with-background-pages")
        options.add_argument("--disable-background-networking")
        
        # === ПРОИЗВОДИТЕЛЬНОСТЬ И СТАБИЛЬНОСТЬ ===
        
        # Отключить ненужные сервисы
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-background-mode")
        
        # === USER AGENT РАНДОМИЗАЦИЯ ===
        
        selected_ua = random.choice(StealthBrowser.USER_AGENTS)
        options.add_argument(f"--user-agent={selected_ua}")
        logger.debug(f"🎭 Selected User-Agent: {selected_ua[:50]}...")
        
        # === ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ПРИВАТНОСТИ ===
        
        # Отключить службы Google
        options.add_argument("--disable-sync")
        options.add_argument("--disable-background-downloads")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-component-update")
        options.add_argument("--disable-datasaver-prompt")
        
        # Управление памятью
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--disable-dev-shm-usage")
        
        # === ЭКСПЕРИМЕНТАЛЬНЫЕ НАСТРОЙКИ ===
        
        # Дополнительные экспериментальные опции для антидетекта
        options.add_experimental_option("prefs", {
            # Отключить уведомления
            "profile.default_content_setting_values.notifications": 2,
            # Отключить геолокацию
            "profile.default_content_setting_values.geolocation": 2,
            # Отключить медиа
            "profile.default_content_setting_values.media_stream": 2,
            # Языковые настройки
            "intl.accept_languages": "en-US,en,ru",
            # Отключить автозаполнение
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False,
        })
        
        logger.info("✅ Stealth Chrome options configured")
        return options
    
    @staticmethod
    def inject_stealth_scripts(driver) -> None:
        """
        Внедрить JavaScript скрипты для маскировки browser fingerprint
        
        Args:
            driver: WebDriver для внедрения скриптов
        """
        logger.info("🔧 Injecting stealth scripts")
        
        try:
            # === ОСНОВНЫЕ STEALTH СКРИПТЫ ===
            
            # 1. Скрыть webdriver property
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            # 2. Переопределить plugins (имитировать реальный браузер)
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            # 3. Модифицировать languages
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'ru']
                });
            """)
            
            # 4. Подмена chrome runtime (если существует)
            driver.execute_script("""
                if (window.chrome && window.chrome.runtime) {
                    Object.defineProperty(window.chrome, 'runtime', {
                        get: () => undefined
                    });
                }
            """)
            
            # 5. Permission API подмена
            driver.execute_script("""
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
            """)
            
            # === РАСШИРЕННЫЕ STEALTH ТЕХНИКИ ===
            
            # 6. Маскировка iframe detection
            driver.execute_script("""
                Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                    get: function() {
                        return window;
                    }
                });
            """)
            
            # 7. Подмена screen properties
            screen_width, screen_height = random.choice(StealthBrowser.SCREEN_RESOLUTIONS)
            driver.execute_script(f"""
                Object.defineProperty(screen, 'width', {{
                    get: () => {screen_width}
                }});
                Object.defineProperty(screen, 'height', {{
                    get: () => {screen_height}
                }});
                Object.defineProperty(screen, 'availWidth', {{
                    get: () => {screen_width}
                }});
                Object.defineProperty(screen, 'availHeight', {{
                    get: () => {screen_height - 50}
                }});
            """)
            
            # 8. Маскировка automation indicators
            driver.execute_script("""
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
            """)
            
            # 9. Hardware concurrency подмена
            cores = random.choice([2, 4, 6, 8, 12, 16])
            driver.execute_script(f"""
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: () => {cores}
                }});
            """)
            
            # 10. Device memory подмена
            memory = random.choice([2, 4, 8, 16])
            driver.execute_script(f"""
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: () => {memory}
                }});
            """)
            
            # 11. Connection подмена
            driver.execute_script("""
                Object.defineProperty(navigator, 'connection', {
                    get: () => ({
                        effectiveType: '4g',
                        rtt: 50,
                        downlink: 10
                    })
                });
            """)
            
            logger.info("✅ Stealth scripts injected successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Some stealth scripts failed to inject: {e}")
    
    @staticmethod
    def randomize_viewport(driver) -> None:
        """
        Рандомизация размера окна браузера
        
        Args:
            driver: WebDriver для изменения размера
        """
        width, height = random.choice(StealthBrowser.SCREEN_RESOLUTIONS)
        
        # Немного уменьшаем для окна браузера (учитываем рамки)
        window_width = width - random.randint(0, 100)
        window_height = height - random.randint(50, 150)
        
        try:
            driver.set_window_size(window_width, window_height)
            logger.info(f"🖥️ Window size set to: {window_width}x{window_height}")
            
            # Случайная позиция окна
            x = random.randint(0, 100)
            y = random.randint(0, 100)
            driver.set_window_position(x, y)
            logger.debug(f"📍 Window position: ({x}, {y})")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to set window size/position: {e}")
    
    @staticmethod
    def add_realistic_headers(driver) -> None:
        """
        Добавить реалистичные HTTP заголовки
        
        Args:
            driver: WebDriver для модификации заголовков
        """
        try:
            # Внедряем скрипт для модификации fetch запросов
            driver.execute_script("""
                const originalFetch = window.fetch;
                window.fetch = function(...args) {
                    if (args[1] && args[1].headers) {
                        args[1].headers = {
                            ...args[1].headers,
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
                            'Accept-Encoding': 'gzip, deflate, br',
                            'DNT': '1',
                            'Upgrade-Insecure-Requests': '1',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'none',
                            'Cache-Control': 'max-age=0'
                        };
                    }
                    return originalFetch.apply(this, args);
                };
            """)
            
            logger.debug("🌐 Realistic headers injection configured")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to add realistic headers: {e}")
    
    @staticmethod
    def mask_automation_vars(driver) -> None:
        """
        Дополнительная маскировка automation переменных
        
        Args:
            driver: WebDriver для маскировки
        """
        try:
            # Список известных automation переменных для удаления
            automation_vars = [
                'window.outerHeight',
                'window.outerWidth', 
                'window.chrome.app',
                'window.chrome.webstore',
                'document.$cdc_asdjflasutopfhvcZLmcfl_',
                'document.documentElement.driver',
                'document.documentElement.webdriver',
                'document.documentElement.selenium',
                'document.documentElement.driver'
            ]
            
            # Удаляем automation переменные
            driver.execute_script("""
                // Удаляем все переменные содержащие 'cdc_'
                for (let prop in window) {
                    if (prop.includes('cdc_')) {
                        delete window[prop];
                    }
                }
                
                // Дополнительная очистка
                if (window.navigator.webdriver) {
                    delete window.navigator.webdriver;
                }
            """)
            
            logger.debug("🧹 Additional automation variables masked")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to mask automation vars: {e}")
    
    @staticmethod
    def setup_full_stealth_mode(driver) -> None:
        """
        Полная настройка stealth режима (вызывать после создания driver)
        
        Args:
            driver: WebDriver для настройки
        """
        logger.info("🚀 Setting up full stealth mode")
        
        try:
            # 1. Основные stealth скрипты
            StealthBrowser.inject_stealth_scripts(driver)
            
            # 2. Рандомизация viewport
            StealthBrowser.randomize_viewport(driver)
            
            # 3. Реалистичные заголовки
            StealthBrowser.add_realistic_headers(driver)
            
            # 4. Дополнительная маскировка
            StealthBrowser.mask_automation_vars(driver)
            
            logger.info("✅ Full stealth mode configured successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup full stealth mode: {e}")
            raise
    
    @staticmethod
    def verify_stealth_setup(driver) -> Dict[str, Any]:
        """
        Проверить эффективность stealth настроек
        
        Args:
            driver: WebDriver для проверки
            
        Returns:
            Dict: Результаты проверки
        """
        logger.info("🔍 Verifying stealth setup")
        
        results = {}
        
        try:
            # Проверка webdriver property
            webdriver_hidden = driver.execute_script("return navigator.webdriver === undefined;")
            results['webdriver_hidden'] = webdriver_hidden
            
            # Проверка chrome runtime
            chrome_runtime_hidden = driver.execute_script("return window.chrome && window.chrome.runtime === undefined;")
            results['chrome_runtime_hidden'] = chrome_runtime_hidden
            
            # Проверка plugins
            plugins_count = driver.execute_script("return navigator.plugins.length;")
            results['plugins_count'] = plugins_count
            
            # Проверка User Agent
            user_agent = driver.execute_script("return navigator.userAgent;")
            results['user_agent'] = user_agent
            
            # Общий результат
            stealth_score = sum([
                webdriver_hidden,
                chrome_runtime_hidden,
                plugins_count > 0
            ])
            
            results['stealth_score'] = f"{stealth_score}/3"
            results['stealth_effective'] = stealth_score >= 2
            
            logger.info(f"🎯 Stealth verification results: {results['stealth_score']} - {'✅ Effective' if results['stealth_effective'] else '⚠️ Needs improvement'}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Stealth verification failed: {e}")
            return {'error': str(e)}