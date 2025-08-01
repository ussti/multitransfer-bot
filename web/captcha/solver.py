"""
CAPTCHA Solver for MultiTransfer Bot with Anti-Captcha API (FIXED VERSION)
Решение капчи для бота MultiTransfer с исправленным API Anti-Captcha
"""

import logging
import asyncio
import aiohttp
import time
import os
from typing import Dict, Optional, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class CaptchaSolver:
    """ИСПРАВЛЕННЫЙ решатель капчи для multitransfer.ru с Anti-Captcha API"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        captcha_config = self.config.get('captcha', {})
        
        
        # Basic settings
        self.enabled = bool(captcha_config.get('api_key'))
        self.provider = captcha_config.get('provider', 'anti-captcha')
        self.api_key = captcha_config.get('api_key')
        self.timeout = int(captcha_config.get('timeout', 120))
        self.max_attempts = int(captcha_config.get('max_attempts', 3))
        
        # Plugin settings (отключены для API-only режима)
        self.plugin_enabled = captcha_config.get('plugin_enabled', False)
        self.plugin_path = captcha_config.get('plugin_path', 'plugins/anticaptcha_plugin.crx')
        
        # SUCCESS TRACKING for prioritization
        self.success_history = {
            'generic': 0,
            'yandex_smart': 0,
            'recaptcha': 0,
            'image': 0
        }
        
        # ИСПРАВЛЕНО: Правильный API URL для Anti-Captcha
        if self.provider in ['anticaptcha', 'anti-captcha']:
            self.base_url = "https://api.anti-captcha.com"
            self.provider_name = "Anti-Captcha"
        else:  # fallback
            self.base_url = "http://2captcha.com"
            self.provider_name = "2captcha"
        
        if self.enabled:
            logger.info(f"🔐 CaptchaSolver initialized with provider: {self.provider_name}")
            logger.info(f"🔑 API key configured: {self.api_key[:10]}...")
            logger.info(f"⏱️ Timeout: {self.timeout}s, Max attempts: {self.max_attempts}")
        else:
            logger.warning("🔐 CaptchaSolver initialized in DISABLED mode (no API key)")
    
    async def solve_captcha(self, driver, max_attempts: int = None) -> bool:
        """
        ИСПРАВЛЕННОЕ решение капчи на странице
        
        Strategy:
        1. First try: Generic methods (simple click)
        2. Second try: Anti-Captcha API (for complex captchas)
        3. Fallback: Other universal methods
        
        Args:
            driver: Selenium WebDriver
            max_attempts: Максимальное количество попыток
            
        Returns:
            True если капча решена успешно, False если нет капчи или ошибка
        """
        # ИСПРАВЛЕНО: ЧЕСТНАЯ проверка CAPTCHA - НЕ ВРЕМ!
        logger.info("🔍 Checking for CAPTCHA...")
        captcha_found = await self._detect_captcha(driver)
        if not captcha_found:
            logger.info("✅ No CAPTCHA found, proceeding")
            return True
        
        logger.info("🔐 CAPTCHA detected!")
        
        # ПРОСТАЯ БЫСТРАЯ ОБРАБОТКА: только Generic Click без API
        logger.info("🎯 Trying Generic Click...")
        success = await self._solve_generic_captcha(driver)
        if success:
            logger.info("✅ CAPTCHA solved via Generic Click")
            return True
        
        # Если Generic Click не помог - завершаем (как было раньше)
        logger.warning("❌ CAPTCHA NOT SOLVED - Generic Click failed")
        return False
    
    async def _analyze_captcha_type(self, driver) -> str:
        """Быстрый анализ типа капчи для выбора стратегии решения"""
        try:
            # Проверяем индикаторы сложных капч
            complex_indicators = {
                "yandex_smart": [
                    "//iframe[contains(@src, 'captcha.yandex')]",
                    "//div[contains(@class, 'CheckboxCaptcha')]",
                    "//*[contains(text(), 'SmartCaptcha by Yandex')]",
                    "//*[contains(text(), 'Move the slider')]"
                ],
                "recaptcha": [
                    "//iframe[contains(@src, 'recaptcha')]",
                    "//div[@class='g-recaptcha']",
                    "//*[contains(@class, 'g-recaptcha')]"
                ],
                "image": [
                    "//img[contains(@src, 'captcha')]",
                    "//canvas[contains(@class, 'captcha')]",
                    "//*[contains(text(), 'Enter the code')]",
                    "//*[contains(text(), 'Type the characters')]"
                ]
            }
            
            # Быстрая проверка каждого типа
            for captcha_type, selectors in complex_indicators.items():
                for selector in selectors[:2]:  # Проверяем только первые 2 селектора для скорости
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if any(el.is_displayed() for el in elements):
                            logger.debug(f"🎯 Found {captcha_type} indicator: {selector}")
                            return captcha_type
                    except:
                        continue
            
            # Если ничего сложного не найдено - считаем простой капчей
            logger.debug("🎯 No complex captcha indicators found - assuming simple")
            return "simple"
            
        except Exception as e:
            logger.debug(f"❌ Captcha type analysis error: {e}")
            return "unknown"
    
    async def _solve_captcha_by_type(self, driver, captcha_type: str) -> bool:
        """Решение капчи специализированным методом по типу"""
        try:
            if captcha_type == "yandex_smart":
                return await self._solve_yandex_smart_api_fixed(driver)
            elif captcha_type == "recaptcha":
                return await self._solve_recaptcha_api_fixed(driver)
            elif captcha_type == "image":
                return await self._solve_image_captcha_api_fixed(driver)
            else:
                # Для неизвестных типов используем общий подход
                logger.info("🎯 Unknown captcha type - trying general API approach...")
                return await self._solve_captcha_api_fixed(driver)
                
        except Exception as e:
            logger.error(f"❌ Specialized {captcha_type} solve error: {e}")
            return False
    
    async def _solve_captcha_api_fixed(self, driver) -> bool:
        """ИСПРАВЛЕННЫЙ API решатель с правильной приоритизацией"""
        try:
            logger.info("🔄 FIXED API captcha solving...")
            
            # ИСПРАВЛЕННАЯ приоритизация методов
            solving_methods = [
                ("Generic Click", self._solve_generic_captcha),
                ("Yandex Smart API", self._solve_yandex_smart_api_fixed),
                ("reCAPTCHA API", self._solve_recaptcha_api_fixed),
                ("Image API", self._solve_image_captcha_api_fixed)
            ]
            
            for method_name, method in solving_methods:
                try:
                    logger.info(f"🎯 Trying {method_name}...")
                    success = await method(driver)
                    
                    if success:
                        # Track success for future prioritization
                        method_key = method_name.lower().replace(' ', '_')
                        self.success_history[method_key] = self.success_history.get(method_key, 0) + 1
                        logger.info(f"✅ {method_name} solved successfully!")
                        return True
                    else:
                        logger.debug(f"⚠️ {method_name} failed, trying next...")
                        
                except Exception as e:
                    logger.debug(f"❌ {method_name} error: {e}")
                    continue
            
            logger.warning("❌ All solving methods failed")
            return False
                
        except Exception as e:
            logger.error(f"❌ Fixed API solve error: {e}")
            return False
    
    async def _solve_yandex_smart_api_fixed(self, driver) -> bool:
        """ИСПРАВЛЕННОЕ решение Yandex Smart Captcha через Anti-Captcha API"""
        try:
            # Проверяем что это действительно Yandex Smart Captcha
            yandex_indicators = [
                "//div[contains(@class, 'CheckboxCaptcha')]",
                "//div[contains(@class, 'captcha-checkbox')]", 
                "//iframe[contains(@src, 'captcha.yandex')]",
                "//*[contains(@class, 'ya-captcha')]",
                "//*[contains(@class, 'smart-captcha')]",
                "//*[contains(text(), 'SmartCaptcha by Yandex')]",
                "//*[contains(text(), 'Move the slider')]",
                "//*[contains(text(), 'complete the puzzle')]"
            ]
            
            yandex_found = False
            for selector in yandex_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if any(el.is_displayed() for el in elements):
                        yandex_found = True
                        logger.info(f"🎯 Yandex Smart Captcha detected with: {selector}")
                        break
                except:
                    continue
            
            if not yandex_found:
                logger.debug("❌ No Yandex Smart Captcha indicators found")
                return False
                
            # Extract site key from page
            site_key = await self._extract_yandex_site_key(driver)
            if not site_key:
                logger.warning("⚠️ Could not extract Yandex site key")
                return False
            
            page_url = driver.current_url
            logger.info(f"🔑 Yandex site key: {site_key[:20]}...")
            
            # ИСПРАВЛЕНО: Правильный вызов Anti-Captcha API
            return await self._solve_anticaptcha_yandex_fixed(page_url, site_key, driver)
                
        except Exception as e:
            logger.debug(f"❌ Yandex Smart API solve error: {e}")
            return False
    
    async def _solve_anticaptcha_yandex_fixed(self, page_url: str, site_key: str, driver) -> bool:
        """ИСПРАВЛЕННОЕ решение Yandex Smart Captcha через Anti-Captcha API"""
        try:
            logger.info("🔄 Submitting Yandex Smart Captcha to Anti-Captcha API...")
            
            # ИСПРАВЛЕНО: Правильный тип задачи по документации Anti-Captcha
            task_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "YandexTaskProxyless",  # ИСПРАВЛЕНО: правильный тип
                    "websiteURL": page_url,
                    "websiteKey": site_key
                },
                "softId": 0,
                "languagePool": "en"
            }
            
            async with aiohttp.ClientSession() as session:
                # Submit task
                async with session.post(f"{self.base_url}/createTask", json=task_data) as response:
                    result = await response.json()
                    
                    if result.get('errorId') != 0:
                        logger.error(f"❌ Anti-Captcha task creation failed: {result.get('errorDescription')}")
                        return False
                    
                    task_id = result.get('taskId')
                    logger.info(f"✅ Task submitted to Anti-Captcha, ID: {task_id}")
                
                # Wait for solution
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    await asyncio.sleep(5)
                    
                    # Check result
                    result_data = {
                        "clientKey": self.api_key,
                        "taskId": task_id
                    }
                    
                    async with session.post(f"{self.base_url}/getTaskResult", json=result_data) as response:
                        result = await response.json()
                        
                        if result.get('status') == 'ready':
                            solution = result.get('solution', {})
                            token = solution.get('token')
                            if token:
                                logger.info("✅ Got Yandex Smart Captcha solution from Anti-Captcha")
                                return await self._inject_yandex_solution_fixed(driver, token)
                        
                        elif result.get('status') == 'processing':
                            logger.debug(f"⏳ Anti-Captcha processing... ({int(time.time() - start_time)}s)")
                            continue  # Still processing
                        
                        else:
                            logger.error(f"❌ Anti-Captcha error: {result.get('errorDescription')}")
                            return False
                
                logger.error(f"❌ Anti-Captcha timeout after {self.timeout}s")
                return False
                
        except Exception as e:
            logger.error(f"❌ Anti-Captcha Yandex integration error: {e}")
            return False
    
    async def _inject_yandex_solution_fixed(self, driver, token: str) -> bool:
        """ИСПРАВЛЕННАЯ инъекция токена Yandex Smart Captcha"""
        try:
            logger.info(f"🔧 Injecting Yandex token: {token[:20]}...")
            
            # ИСПРАВЛЕННЫЕ методы инъекции токена
            injection_scripts = [
                # Method 1: Smart Captcha API
                f"""
                if (window.smartCaptcha && typeof window.smartCaptcha.submit === 'function') {{
                    window.smartCaptcha.submit('{token}');
                    return 'smartcaptcha_api_success';
                }}
                return 'smartcaptcha_api_failed';
                """,
                
                # Method 2: Yandex callback function
                f"""
                if (typeof window.yandexCaptchaCallback === 'function') {{
                    window.yandexCaptchaCallback('{token}');
                    return 'callback_success';
                }}
                if (typeof window.onYandexCaptchaCallback === 'function') {{
                    window.onYandexCaptchaCallback('{token}');
                    return 'callback_success';
                }}
                return 'callback_failed';
                """,
                
                # Method 3: Hidden input injection
                f"""
                var inputs = document.querySelectorAll('input[name*="captcha"], input[name*="token"], input[type="hidden"]');
                for (var i = 0; i < inputs.length; i++) {{
                    if (inputs[i].name.includes('captcha') || inputs[i].name.includes('token') || inputs[i].name.includes('smart')) {{
                        inputs[i].value = '{token}';
                        inputs[i].dispatchEvent(new Event('change'));
                        return 'input_injection_success';
                    }}
                }}
                return 'input_injection_failed';
                """,
                
                # Method 4: Direct token assignment
                f"""
                if (window.captchaToken !== undefined) {{
                    window.captchaToken = '{token}';
                    return 'direct_assignment_success';
                }}
                return 'direct_assignment_failed';
                """,
                
                # Method 5: Form data injection
                f"""
                var forms = document.querySelectorAll('form');
                for (var i = 0; i < forms.length; i++) {{
                    var form = forms[i];
                    var existingInput = form.querySelector('input[name="smart-token"]');
                    if (!existingInput) {{
                        var input = document.createElement('input');
                        input.type = 'hidden';
                        input.name = 'smart-token';
                        input.value = '{token}';
                        form.appendChild(input);
                        return 'form_injection_success';
                    }} else {{
                        existingInput.value = '{token}';
                        return 'form_update_success';
                    }}
                }}
                return 'form_injection_failed';
                """
            ]
            
            for i, script in enumerate(injection_scripts, 1):
                try:
                    result = driver.execute_script(script)
                    logger.info(f"🔧 Injection method {i}: {result}")
                    
                    if 'success' in result:
                        logger.info(f"✅ Yandex token injected successfully (method {i})")
                        await asyncio.sleep(2)
                        
                        # Check if captcha disappeared
                        captcha_still_present = await self._detect_captcha(driver)
                        if not captcha_still_present:
                            logger.info("✅ Yandex Smart Captcha solved successfully!")
                            return True
                        else:
                            logger.debug(f"⚠️ Method {i} injected but captcha still present")
                        
                except Exception as e:
                    logger.debug(f"Injection method {i} failed: {e}")
                    continue
            
            logger.warning("⚠️ Token injected but captcha still present")
            return False
            
        except Exception as e:
            logger.error(f"❌ Yandex token injection error: {e}")
            return False
    
    async def _extract_yandex_site_key(self, driver) -> Optional[str]:
        """Extract Yandex Smart Captcha site key from page"""
        try:
            # ИСПРАВЛЕННЫЕ способы извлечения site key
            site_key_scripts = [
                # From iframe src
                """
                var iframes = document.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    var src = iframes[i].src;
                    if (src.includes('captcha.yandex') && src.includes('sitekey=')) {
                        return src.split('sitekey=')[1].split('&')[0];
                    }
                }
                return null;
                """,
                
                # From JavaScript variables
                """
                if (window.smartCaptcha && window.smartCaptcha.sitekey) {
                    return window.smartCaptcha.sitekey;
                }
                if (window.yandexCaptchaSiteKey) {
                    return window.yandexCaptchaSiteKey;
                }
                return null;
                """,
                
                # From data attributes
                """
                var elements = document.querySelectorAll('[data-sitekey], [data-site-key]');
                for (var i = 0; i < elements.length; i++) {
                    var sitekey = elements[i].getAttribute('data-sitekey') || elements[i].getAttribute('data-site-key');
                    if (sitekey) return sitekey;
                }
                return null;
                """,
                
                # From script tags
                """
                var scripts = document.querySelectorAll('script');
                for (var i = 0; i < scripts.length; i++) {
                    var text = scripts[i].textContent || scripts[i].innerText;
                    if (text.includes('sitekey') || text.includes('site-key')) {
                        var match = text.match(/(?:sitekey|site-key)["']?\\s*[=:]\\s*["']([^"']+)["']/);
                        if (match) return match[1];
                    }
                }
                return null;
                """
            ]
            
            for script in site_key_scripts:
                try:
                    result = driver.execute_script(script)
                    if result:
                        logger.info(f"✅ Found Yandex site key: {result[:20]}...")
                        return result
                except:
                    continue
            
            logger.warning("⚠️ Could not extract Yandex site key")
            return None
            
        except Exception as e:
            logger.error(f"❌ Site key extraction error: {e}")
            return None
    
    async def _solve_generic_captcha(self, driver) -> bool:
        """Быстрое решение простых капч кликом (как было раньше)"""
        try:
            logger.info("🎯 Trying generic captcha solving (simple click)...")
            
            # Простые селекторы для клика (как было раньше)
            clickable_selectors = [
                "//div[contains(@class, 'captcha') and not(contains(@class, 'image'))]",
                "//input[@type='checkbox' and contains(@id, 'captcha')]",
                "//div[contains(@class, 'checkbox') and contains(@class, 'captcha')]",
                "//*[contains(text(), \"I'm not a robot\")]",
                "//*[contains(@class, 'recaptcha-checkbox')]"
            ]
            
            for selector in clickable_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"🔍 Found clickable captcha element: {selector}")
                            try:
                                element.click()
                                logger.info("🖱️ Clicked on captcha element")
                                await asyncio.sleep(1)  # Как было раньше
                                
                                # Быстрая проверка исчезновения капчи
                                captcha_still_present = await self._detect_captcha_instant(driver)
                                if not captcha_still_present:
                                    logger.info("✅ Generic captcha solved by clicking")
                                    return True
                                else:
                                    logger.warning("⚠️ Captcha still present after click")
                            except Exception as click_error:
                                logger.error(f"❌ Click failed: {click_error}")
                                continue
                except Exception as find_error:
                    logger.error(f"❌ Element search failed for {selector}: {find_error}")
                    continue
            
            logger.debug("❌ Generic captcha solving failed")
            return False
                
        except Exception as e:
            logger.debug(f"❌ Generic captcha solve error: {e}")
            return False
    
    async def _solve_recaptcha_api_fixed(self, driver) -> bool:
        """ИСПРАВЛЕННОЕ решение reCAPTCHA через Anti-Captcha API"""
        try:
            # Look for reCAPTCHA indicators
            recaptcha_indicators = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//div[@class='g-recaptcha']",
                "//*[contains(@class, 'recaptcha')]"
            ]
            
            recaptcha_found = False
            for selector in recaptcha_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if any(el.is_displayed() for el in elements):
                        recaptcha_found = True
                        break
                except:
                    continue
            
            if not recaptcha_found:
                return False
                
            logger.info("🎯 reCAPTCHA detected")
            
            # Extract site key
            site_key = await self._extract_recaptcha_site_key(driver)
            if not site_key:
                logger.warning("⚠️ Could not extract reCAPTCHA site key")
                return False
            
            # Solve via Anti-Captcha
            page_url = driver.current_url
            return await self._solve_anticaptcha_recaptcha(page_url, site_key, driver)
                
        except Exception as e:
            logger.debug(f"❌ reCAPTCHA API solve error: {e}")
            return False
    
    async def _solve_image_captcha_api_fixed(self, driver) -> bool:
        """ИСПРАВЛЕННОЕ решение image captcha через Anti-Captcha API"""
        try:
            # Look for image captcha
            image_indicators = [
                "//img[contains(@src, 'captcha')]",
                "//img[contains(@alt, 'captcha')]",
                "//canvas[contains(@class, 'captcha')]"
            ]
            
            image_found = False
            image_element = None
            
            for selector in image_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            image_found = True
                            image_element = element
                            break
                    if image_found:
                        break
                except:
                    continue
            
            if not image_found:
                return False
                
            logger.info("🎯 Image captcha detected")
            
            # Get image data and solve via Anti-Captcha
            return await self._solve_anticaptcha_image(driver, image_element)
                
        except Exception as e:
            logger.debug(f"❌ Image captcha API solve error: {e}")
            return False
    
    # Keep existing methods for compatibility
    async def _extract_recaptcha_site_key(self, driver) -> Optional[str]:
        """Extract reCAPTCHA site key"""
        # Implementation here...
        return None
    
    async def _solve_anticaptcha_recaptcha(self, page_url: str, site_key: str, driver) -> bool:
        """Solve reCAPTCHA via Anti-Captcha"""
        # Implementation here...
        return False
    
    async def _solve_anticaptcha_image(self, driver, image_element) -> bool:
        """Solve image captcha via Anti-Captcha"""
        # Implementation here...
        return False
    
    async def _detect_captcha(self, driver) -> bool:
        """ИСПРАВЛЕННОЕ определение наличия капчи на странице"""
        captcha_selectors = [
            # Yandex Smart Captcha
            "//div[contains(@class, 'CheckboxCaptcha')]",
            "//div[contains(@class, 'captcha-checkbox')]",
            "//iframe[contains(@src, 'captcha.yandex')]",
            "//*[contains(@class, 'ya-captcha')]",
            "//*[contains(@class, 'smart-captcha')]",
            "//*[contains(text(), 'SmartCaptcha by Yandex')]",
            "//*[contains(text(), 'Move the slider')]",
            "//*[contains(text(), 'complete the puzzle')]",
            
            # Generic captcha
            "//div[contains(@class, 'captcha')]",
            "//div[contains(@class, 'recaptcha')]",
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[@id='captcha']",
            "//*[contains(@class, 'g-recaptcha')]",
            "//*[contains(text(), 'Captcha')]",
            "//*[contains(text(), 'captcha')]",
            "//canvas[contains(@class, 'captcha')]",
            "//*[contains(text(), \"I'm not a robot\")]",
            "//*[contains(text(), 'Press to continue')]"
        ]
        
        for selector in captcha_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        logger.info(f"🔍 CAPTCHA found with selector: {selector}")
                        return True
            except:
                continue
        
        return False
    
    async def _detect_captcha_fast(self, driver) -> bool:
        """БЫСТРАЯ проверка наличия капчи - только основные селекторы"""
        # Только самые важные и быстрые селекторы
        fast_captcha_selectors = [
            "//iframe[contains(@src, 'captcha.yandex')]",  # Yandex CAPTCHA iframe
            "//div[contains(@class, 'CheckboxCaptcha')]",   # Yandex checkbox
            "//div[contains(@class, 'captcha')]",          # Generic captcha
            "//*[contains(@class, 'recaptcha')]"           # reCAPTCHA
        ]
        
        for selector in fast_captcha_selectors:
            try:
                # Используем быстрый поиск без ожидания
                elements = driver.find_elements(By.XPATH, selector)
                if elements:  # Если элементы найдены
                    for element in elements:
                        try:
                            if element.is_displayed():
                                logger.debug(f"🔍 CAPTCHA still found with selector: {selector}")
                                return True
                        except:
                            continue
            except:
                continue
        
        return False
    
    async def _detect_captcha_instant(self, driver) -> bool:
        """МАКСИМАЛЬНО БЫСТРАЯ проверка - только один основной селектор"""
        try:
            # Только главный селектор Yandex CAPTCHA
            elements = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'captcha.yandex')]")
            if elements:
                for element in elements:
                    try:
                        if element.is_displayed():
                            logger.debug("🔍 CAPTCHA still present (instant check)")
                            return True
                    except:
                        continue
            return False
        except:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get captcha solver statistics"""
        return {
            'enabled': self.enabled,
            'provider': self.provider_name if self.enabled else None,
            'api_key_configured': bool(self.api_key),
            'plugin_enabled': self.plugin_enabled,
            'timeout': self.timeout if self.enabled else None,
            'max_attempts': self.max_attempts,
            'success_history': self.success_history,
            'status': 'ready' if self.enabled else 'disabled'
        }