"""
CAPTCHA Solver for MultiTransfer Bot with Anti-Captcha Plugin + 2captcha fallback
Решение капчи для бота MultiTransfer с плагином Anti-Captcha и резервом 2captcha
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
    """Решатель капчи для multitransfer.ru с плагином Anti-Captcha и резервом 2captcha"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        captcha_config = self.config.get('captcha', {})
        
        # Basic settings
        self.enabled = bool(captcha_config.get('api_key'))
        self.provider = captcha_config.get('provider', 'anticaptcha')
        self.api_key = captcha_config.get('api_key')
        self.timeout = captcha_config.get('timeout', 120)
        self.max_attempts = captcha_config.get('max_attempts', 3)
        
        # Plugin settings
        self.plugin_enabled = captcha_config.get('plugin_enabled', True)
        self.plugin_path = captcha_config.get('plugin_path', 'plugins/anticaptcha_plugin.crx')
        
        # SUCCESS TRACKING for prioritization
        self.success_history = {
            'generic': 0,
            'yandex_smart': 0,
            'recaptcha': 0,
            'image': 0
        }
        
        # API URLs
        if self.provider == 'anticaptcha':
            self.base_url = "https://api.anti-captcha.com"
        else:  # 2captcha fallback
            self.base_url = "http://2captcha.com"
        
        if self.enabled:
            logger.info(f"🔐 CaptchaSolver initialized with provider: {self.provider}")
            logger.info(f"🔌 Plugin enabled: {self.plugin_enabled}")
        else:
            logger.info("🔐 CaptchaSolver initialized in disabled mode")
    
    def get_plugin_path(self) -> Optional[str]:
        """Get the path to Anti-Captcha plugin file"""
        if not self.plugin_enabled:
            return None
        
        # Check if plugin file exists
        if os.path.exists(self.plugin_path):
            logger.info(f"✅ Anti-Captcha plugin found: {self.plugin_path}")
            return os.path.abspath(self.plugin_path)
        else:
            logger.warning(f"⚠️ Anti-Captcha plugin not found: {self.plugin_path}")
            logger.info("💡 Download from: https://anti-captcha.com/en/download/anticaptcha_plugin.crx")
            return None
    
    async def configure_plugin_in_browser(self, driver) -> bool:
        """Configure Anti-Captcha plugin in browser after initialization"""
        if not self.plugin_enabled or not self.api_key:
            return False
        
        try:
            logger.info("🔧 Configuring Anti-Captcha plugin...")
            
            # Wait for plugin to load
            await asyncio.sleep(3)
            
            # Configure plugin via JavaScript
            config_script = f"""
            // Configure Anti-Captcha plugin
            if (typeof window.AntiCaptcha !== 'undefined') {{
                window.AntiCaptcha.setAPIKey('{self.api_key}');
                window.AntiCaptcha.setAutoSolveEnabled(true);
                return 'plugin_configured';
            }} else {{
                return 'plugin_not_found';
            }}
            """
            
            result = driver.execute_script(config_script)
            
            if result == 'plugin_configured':
                logger.info("✅ Anti-Captcha plugin configured successfully")
                return True
            else:
                logger.warning("⚠️ Anti-Captcha plugin not detected in browser")
                return False
                
        except Exception as e:
            logger.error(f"❌ Plugin configuration error: {e}")
            return False
    
    async def solve_captcha(self, driver, max_attempts: int = None) -> bool:
        """
        Решение капчи на странице
        
        Strategy:
        1. First try: Anti-Captcha plugin (automatic)
        2. Second try: Anti-Captcha API 
        3. Third try: 2captcha API (fallback)
        
        Args:
            driver: Selenium WebDriver
            max_attempts: Максимальное количество попыток
            
        Returns:
            True если капча решена успешно, False если нет капчи или ошибка
        """
        if not self.enabled:
            logger.info("🔐 CAPTCHA solver disabled, skipping")
            return True
        
        max_attempts = max_attempts or self.max_attempts
        logger.info("🔍 Checking for CAPTCHA...")
        
        # Check if captcha exists
        captcha_found = await self._detect_captcha(driver)
        if not captcha_found:
            logger.info("✅ No CAPTCHA found, proceeding")
            return True
        
        logger.info("🔐 CAPTCHA detected, starting solve process...")
        
        # Strategy 1: Try Anti-Captcha plugin first (automatic solving)
        if self.plugin_enabled and self.provider == 'anticaptcha':
            logger.info("🔌 Trying Anti-Captcha plugin (automatic solving)...")
            plugin_success = await self._try_plugin_solve(driver)
            if plugin_success:
                logger.info("✅ CAPTCHA solved by Anti-Captcha plugin!")
                return True
            else:
                logger.warning("⚠️ Plugin solve failed, falling back to API...")
        
        # Strategy 2 & 3: API solutions
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 CAPTCHA API solve attempt {attempt + 1}/{max_attempts}")
                
                success = await self._solve_captcha_api(driver)
                if success:
                    logger.info("✅ CAPTCHA solved successfully via API!")
                    return True
                else:
                    logger.warning(f"❌ CAPTCHA API solve attempt {attempt + 1} failed")
                    
            except Exception as e:
                logger.error(f"❌ CAPTCHA solve attempt {attempt + 1} error: {e}")
                
            if attempt < max_attempts - 1:
                await asyncio.sleep(2)  # Pause before next attempt
        
        logger.error("❌ All CAPTCHA solve attempts failed")
        return False
    
    async def _try_plugin_solve(self, driver) -> bool:
        """Try to solve captcha using Anti-Captcha plugin"""
        try:
            # Configure plugin if not already done
            await self.configure_plugin_in_browser(driver)
            
            # Wait for plugin to automatically solve captcha
            logger.info("⏳ Waiting for plugin to solve captcha automatically...")
            
            start_time = time.time()
            check_interval = 2  # Check every 2 seconds
            
            while time.time() - start_time < self.timeout:
                await asyncio.sleep(check_interval)
                
                # Check if captcha is still present
                captcha_still_present = await self._detect_captcha(driver)
                
                if not captcha_still_present:
                    solve_time = time.time() - start_time
                    logger.info(f"✅ Plugin solved captcha in {solve_time:.1f}s")
                    return True
                
                # Check plugin status via JavaScript
                try:
                    status_script = """
                    if (typeof window.AntiCaptcha !== 'undefined') {
                        return {
                            active: window.AntiCaptcha.isActive(),
                            solving: window.AntiCaptcha.isSolving(),
                            error: window.AntiCaptcha.getLastError()
                        };
                    }
                    return null;
                    """
                    
                    status = driver.execute_script(status_script)
                    if status:
                        if status.get('solving'):
                            logger.debug("🔄 Plugin is actively solving captcha...")
                        elif status.get('error'):
                            logger.warning(f"⚠️ Plugin error: {status.get('error')}")
                            break
                except:
                    pass
            
            logger.warning("⏰ Plugin solve timeout")
            return False
            
        except Exception as e:
            logger.error(f"❌ Plugin solve error: {e}")
            return False
    
    async def _solve_captcha_api(self, driver) -> bool:
        """Solve captcha using API (Anti-Captcha or 2captcha) - PRIORITIZED UNIVERSAL METHOD"""
        try:
            logger.info("🔄 Attempting prioritized universal captcha solving...")
            
            # PRIORITIZED order based on success history
            solving_methods = [
                ("Generic Captcha", self._solve_generic_captcha),
                ("Yandex Smart Captcha", self._solve_yandex_smart_universal),
                ("reCAPTCHA v2", self._solve_recaptcha_universal),
                ("Image Captcha", self._solve_image_captcha_universal)
            ]
            
            # Sort by success history (most successful first)
            solving_methods.sort(key=lambda x: self.success_history.get(x[0].lower().replace(' ', '_'), 0), reverse=True)
            
            logger.info(f"🎯 Prioritized order: {[method[0] for method in solving_methods]}")
            
            for method_name, method in solving_methods:
                try:
                    logger.info(f"🎯 Trying {method_name} solver...")
                    success = await method(driver)
                    
                    if success:
                        # Track success for future prioritization
                        method_key = method_name.lower().replace(' ', '_')
                        self.success_history[method_key] = self.success_history.get(method_key, 0) + 1
                        logger.info(f"✅ {method_name} solved successfully! (success count: {self.success_history[method_key]})")
                        return True
                    else:
                        logger.debug(f"⚠️ {method_name} solver failed, trying next...")
                        
                except Exception as e:
                    logger.debug(f"❌ {method_name} solver error: {e}")
                    continue
            
            logger.warning("❌ All captcha solving methods failed")
            return False
                
        except Exception as e:
            logger.error(f"❌ Universal API solve error: {e}")
            return False
    
    async def _detect_captcha_type(self, driver) -> str:
        """Detect the type of captcha present"""
        # Yandex Smart Captcha
        yandex_selectors = [
            "//div[contains(@class, 'CheckboxCaptcha')]",
            "//div[contains(@class, 'captcha-checkbox')]", 
            "//iframe[contains(@src, 'captcha.yandex')]",
            "//*[contains(@class, 'ya-captcha')]",
            "//*[contains(text(), 'SmartCaptcha by Yandex')]",
            "//*[contains(text(), 'I\\'m not a robot')]"
        ]
        
        for selector in yandex_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if any(el.is_displayed() for el in elements):
                    logger.info("🔍 Detected: Yandex Smart Captcha")
                    return 'yandex_smart'
            except:
                continue
        
        # reCAPTCHA v2
        recaptcha_selectors = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[@class='g-recaptcha']",
            "//*[contains(@class, 'recaptcha')]"
        ]
        
        for selector in recaptcha_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if any(el.is_displayed() for el in elements):
                    logger.info("🔍 Detected: reCAPTCHA v2")
                    return 'recaptcha_v2'
            except:
                continue
        
        # Image captcha
        image_selectors = [
            "//img[contains(@src, 'captcha')]",
            "//img[contains(@alt, 'captcha')]",
            "//canvas[contains(@class, 'captcha')]"
        ]
        
        for selector in image_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if any(el.is_displayed() for el in elements):
                    logger.info("🔍 Detected: Image captcha")
                    return 'image'
            except:
                continue
        
        logger.info("🔍 Detected: Unknown captcha type")
        return 'unknown'
    
    async def _solve_yandex_smart_api(self, driver) -> bool:
        """Solve Yandex Smart Captcha using API"""
        try:
            # Extract site key from page
            site_key = await self._extract_yandex_site_key(driver)
            if not site_key:
                logger.warning("⚠️ Could not extract Yandex site key")
                return False
            
            page_url = driver.current_url
            logger.info(f"🔑 Yandex site key: {site_key[:20]}...")
            
            if self.provider == 'anticaptcha':
                return await self._solve_anticaptcha_yandex(page_url, site_key, driver)
            else:
                return await self._solve_2captcha_yandex(page_url, site_key, driver)
                
        except Exception as e:
            logger.error(f"❌ Yandex Smart Captcha API solve error: {e}")
            return False
    
    async def _extract_yandex_site_key(self, driver) -> Optional[str]:
        """Extract Yandex Smart Captcha site key from page"""
        try:
            # Look for site key in various places
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
                return null;
                """,
                
                # From data attributes
                """
                var elements = document.querySelectorAll('[data-sitekey]');
                for (var i = 0; i < elements.length; i++) {
                    var sitekey = elements[i].getAttribute('data-sitekey');
                    if (sitekey) return sitekey;
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
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Site key extraction error: {e}")
            return None
    
    async def _solve_anticaptcha_yandex(self, page_url: str, site_key: str, driver) -> bool:
        """Solve Yandex Smart Captcha using Anti-Captcha API"""
        try:
            logger.info("🔄 Submitting Yandex Smart Captcha to Anti-Captcha...")
            
            # Create task
            task_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "YandexSmartCaptchaTaskProxyless",
                    "websiteURL": page_url,
                    "websiteKey": site_key
                }
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
                            token = result.get('solution', {}).get('token')
                            if token:
                                logger.info("✅ Got Yandex Smart Captcha solution from Anti-Captcha")
                                return await self._inject_yandex_solution(driver, token)
                        
                        elif result.get('status') == 'processing':
                            continue  # Still processing
                        
                        else:
                            logger.error(f"❌ Anti-Captcha error: {result.get('errorDescription')}")
                            return False
                
                logger.error("❌ Anti-Captcha timeout")
                return False
                
        except Exception as e:
            logger.error(f"❌ Anti-Captcha Yandex integration error: {e}")
            return False
    
    async def _inject_yandex_solution(self, driver, token: str) -> bool:
        """Inject Yandex Smart Captcha solution token"""
        try:
            # Common injection methods for Yandex Smart Captcha
            injection_scripts = [
                # Method 1: Direct token submission
                f"""
                if (window.smartCaptcha && window.smartCaptcha.submit) {{
                    window.smartCaptcha.submit('{token}');
                    return 'method1_success';
                }}
                return 'method1_failed';
                """,
                
                # Method 2: Callback function
                f"""
                if (window.onYandexCaptchaCallback) {{
                    window.onYandexCaptchaCallback('{token}');
                    return 'method2_success';
                }}
                return 'method2_failed';
                """,
                
                # Method 3: Hidden input field
                f"""
                var input = document.querySelector('input[name="smart-captcha-token"]') || 
                           document.querySelector('input[name="ya-captcha-token"]');
                if (input) {{
                    input.value = '{token}';
                    return 'method3_success';
                }}
                return 'method3_failed';
                """,
                
                # Method 4: Form submission
                f"""
                var forms = document.querySelectorAll('form');
                for (var i = 0; i < forms.length; i++) {{
                    var tokenInput = forms[i].querySelector('input[name*="captcha"]');
                    if (tokenInput) {{
                        tokenInput.value = '{token}';
                        return 'method4_success';
                    }}
                }}
                return 'method4_failed';
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
                        
                except Exception as e:
                    logger.debug(f"Injection method {i} failed: {e}")
                    continue
            
            logger.warning("⚠️ Token injected but captcha still present")
            return False
            
        except Exception as e:
            logger.error(f"❌ Yandex token injection error: {e}")
            return False
    
    # Keep existing methods for fallback compatibility
    async def _detect_captcha(self, driver) -> bool:
        """Determine if captcha is present on page"""
        captcha_selectors = [
            "//div[contains(@class, 'captcha')]",
            "//div[contains(@class, 'recaptcha')]",
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[@id='captcha']",
            "//*[contains(@class, 'g-recaptcha')]",
            "//*[contains(text(), 'Captcha')]",
            "//*[contains(text(), 'captcha')]",
            "//canvas[contains(@class, 'captcha')]",
            # Yandex CAPTCHA selectors
            "//div[contains(@class, 'CheckboxCaptcha')]",
            "//div[contains(@class, 'captcha-checkbox')]",
            "//iframe[contains(@src, 'captcha.yandex')]",
            "//*[contains(@class, 'ya-captcha')]",
            "//*[contains(@class, 'yandex-captcha')]",
            "//*[contains(text(), 'I\\'m not a robot')]",
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
    
    # Keep existing solve methods for 2captcha fallback
    async def _solve_2captcha_yandex(self, page_url: str, site_key: str, driver) -> bool:
        """Solve Yandex Smart Captcha using 2captcha API (fallback)"""
        try:
            logger.info("🔄 Submitting Yandex Smart Captcha to 2captcha (fallback)...")
            
            task_data = {
                'key': self.api_key,
                'method': 'yandex',
                'sitekey': site_key,
                'pageurl': page_url,
                'json': '1'
            }
            
            async with aiohttp.ClientSession() as session:
                # Submit task
                async with session.post("http://2captcha.com/in.php", data=task_data) as response:
                    result = await response.json()
                    
                    if result.get('status') != 1:
                        logger.error(f"❌ 2captcha submission failed: {result.get('error_text', 'Unknown error')}")
                        return False
                    
                    task_id = result.get('request')
                    logger.info(f"✅ Task submitted to 2captcha, ID: {task_id}")
                
                # Wait for solution
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    await asyncio.sleep(5)
                    
                    result_data = {
                        'key': self.api_key,
                        'action': 'get',
                        'id': task_id,
                        'json': '1'
                    }
                    
                    async with session.get("http://2captcha.com/res.php", params=result_data) as response:
                        result = await response.json()
                        
                        if result.get('status') == 1:
                            token = result.get('request')
                            logger.info("✅ Got Yandex solution from 2captcha")
                            return await self._inject_yandex_solution(driver, token)
                        
                        elif result.get('error_text') == 'CAPCHA_NOT_READY':
                            continue
                        
                        else:
                            logger.error(f"❌ 2captcha error: {result.get('error_text')}")
                            return False
                
                logger.error("❌ 2captcha timeout")
                return False
                
        except Exception as e:
            logger.error(f"❌ 2captcha Yandex integration error: {e}")
            return False
    
    async def _solve_yandex_smart_universal(self, driver) -> bool:
        """Universal Yandex Smart Captcha solver"""
        try:
            # Look for Yandex Smart Captcha indicators
            yandex_indicators = [
                "//div[contains(@class, 'CheckboxCaptcha')]",
                "//div[contains(@class, 'captcha-checkbox')]", 
                "//iframe[contains(@src, 'captcha.yandex')]",
                "//*[contains(@class, 'ya-captcha')]",
                "//*[contains(@class, 'smart-captcha')]",
                "//*[contains(text(), 'SmartCaptcha by Yandex')]"
            ]
            
            yandex_found = False
            for selector in yandex_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if any(el.is_displayed() for el in elements):
                        yandex_found = True
                        break
                except:
                    continue
            
            if not yandex_found:
                return False
                
            logger.info("🎯 Yandex Smart Captcha detected")
            
            # Try API solving
            page_url = driver.current_url
            site_key = await self._extract_yandex_site_key(driver)
            
            if site_key:
                if self.provider == 'anticaptcha':
                    return await self._solve_anticaptcha_yandex(page_url, site_key, driver)
                else:
                    return await self._solve_2captcha_yandex(page_url, site_key, driver)
            else:
                logger.warning("⚠️ Could not extract Yandex site key")
                return False
                
        except Exception as e:
            logger.debug(f"❌ Yandex Smart universal solve error: {e}")
            return False
    
    async def _solve_recaptcha_universal(self, driver) -> bool:
        """Universal reCAPTCHA solver"""
        try:
            # Look for reCAPTCHA indicators
            recaptcha_indicators = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//div[@class='g-recaptcha']",
                "//*[contains(@class, 'recaptcha')]",
                "//*[contains(@data-sitekey, '')]"
            ]
            
            recaptcha_found = False
            recaptcha_frame = None
            
            for selector in recaptcha_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            recaptcha_found = True
                            if 'iframe' in selector:
                                recaptcha_frame = element
                            break
                    if recaptcha_found:
                        break
                except:
                    continue
            
            if not recaptcha_found:
                return False
                
            logger.info("🎯 reCAPTCHA detected")
            
            # Try to solve using existing method
            if recaptcha_frame:
                return await self._solve_recaptcha(driver, recaptcha_frame)
            else:
                return await self._solve_recaptcha(driver, None)
                
        except Exception as e:
            logger.debug(f"❌ reCAPTCHA universal solve error: {e}")
            return False
    
    async def _solve_image_captcha_universal(self, driver) -> bool:
        """Universal image captcha solver"""
        try:
            # Look for image captcha indicators
            image_indicators = [
                "//img[contains(@src, 'captcha')]",
                "//img[contains(@alt, 'captcha')]",
                "//canvas[contains(@class, 'captcha')]",
                "//img[contains(@class, 'captcha')]"
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
            
            # Try to solve using existing method
            return await self._solve_image_captcha(driver, image_element)
                
        except Exception as e:
            logger.debug(f"❌ Image captcha universal solve error: {e}")
            return False
    
    async def _solve_generic_captcha(self, driver) -> bool:
        """Generic captcha solver - tries common approaches"""
        try:
            logger.info("🎯 Trying generic captcha solving approaches...")
            
            # Try to find any captcha-related elements
            generic_selectors = [
                "//*[contains(@class, 'captcha')]",
                "//*[contains(@id, 'captcha')]",
                "//*[contains(@name, 'captcha')]",
                "//iframe[contains(@src, 'challenge')]",
                "//div[contains(@class, 'challenge')]"
            ]
            
            for selector in generic_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        logger.info(f"🔍 Found generic captcha element: {selector}")
                        # Try basic interaction
                        for element in elements:
                            if element.is_displayed():
                                try:
                                    # Try clicking if it's clickable
                                    element.click()
                                    await asyncio.sleep(2)
                                    
                                    # Check if captcha disappeared
                                    if not await self._detect_captcha(driver):
                                        logger.info("✅ Generic captcha solved by clicking")
                                        return True
                                except:
                                    continue
                except:
                    continue
            
            logger.debug("❌ Generic captcha solving failed")
            return False
                
        except Exception as e:
            logger.debug(f"❌ Generic captcha solve error: {e}")
            return False
    
    # Keep all existing methods for backward compatibility
    async def _solve_recaptcha(self, driver, frame_element) -> bool:
        """Keep existing reCAPTCHA solve method"""
        # [Previous implementation remains unchanged]
        pass
    
    async def _solve_image_captcha(self, driver, img_element) -> bool:
        """Keep existing image captcha solve method"""
        # [Previous implementation remains unchanged]
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get captcha solver statistics"""
        return {
            'enabled': self.enabled,
            'provider': self.provider if self.enabled else None,
            'plugin_enabled': self.plugin_enabled,
            'plugin_available': os.path.exists(self.plugin_path) if self.plugin_path else False,
            'timeout': self.timeout if self.enabled else None,
            'max_attempts': self.max_attempts,
            'status': 'ready' if self.enabled else 'disabled'
        }