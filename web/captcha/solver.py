"""
OPTIMIZED CAPTCHA Solver - Generic Priority with Fast Performance
Оптимизированный решатель капчи с приоритетом Generic типов для быстрой работы
"""

import logging
import asyncio
import aiohttp
import time
from typing import Dict, Optional, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class CaptchaSolver:
    """Оптимизированный решатель капчи с приоритетом Generic типов"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        captcha_config = self.config.get('captcha', {})
        
        # Оптимизированные настройки для быстрой работы
        self.enabled = bool(captcha_config.get('api_key'))
        self.provider = captcha_config.get('provider', 'anti-captcha')
        self.api_key = captcha_config.get('api_key')
        
        # БЫСТРЫЕ ТАЙМАУТЫ для производительности
        self.timeout = min(captcha_config.get('timeout', 30), 30)  # Максимум 30 сек
        self.max_attempts = min(captcha_config.get('max_attempts', 2), 2)  # Максимум 2 попытки
        self.generic_timeout = 15  # Быстрый таймаут для Generic
        
        # API URLs
        if self.provider == 'anti-captcha':
            self.base_url = "https://api.anti-captcha.com"
        else:
            self.base_url = "http://2captcha.com"
        
        if self.enabled:
            logger.info(f"🔐 OPTIMIZED CaptchaSolver initialized: {self.provider} (timeout: {self.timeout}s)")
        else:
            logger.info("🔐 CaptchaSolver disabled - no API key")
    
    async def solve_captcha(self, driver, max_attempts: int = None) -> bool:
        """
        ОПТИМИЗИРОВАННОЕ решение капчи с приоритетом Generic типов
        
        Стратегия:
        1. Generic Captcha (15 сек) - основной метод
        2. Если не сработал - только один API метод (15 сек)
        3. Максимальное время: 30 секунд
        
        Args:
            driver: Selenium WebDriver
            max_attempts: Максимальное количество попыток
            
        Returns:
            True если капча решена или отсутствует, False при ошибке
        """
        if not self.enabled:
            logger.info("🔐 CAPTCHA solver disabled, skipping")
            return True
        
        max_attempts = max_attempts or self.max_attempts
        start_time = time.time()
        
        logger.info("🔍 Quick CAPTCHA detection...")
        
        # Быстрое обнаружение капчи (3 сек максимум)
        captcha_found = await self._quick_detect_captcha(driver)
        if not captcha_found:
            logger.info("✅ No CAPTCHA found, proceeding")
            return True
        
        logger.info("🔐 CAPTCHA detected, starting OPTIMIZED solve...")
        
        # ОПТИМИЗИРОВАННАЯ СТРАТЕГИЯ: Generic первым и основным
        for attempt in range(max_attempts):
            try:
                elapsed = time.time() - start_time
                remaining_time = self.timeout - elapsed
                
                if remaining_time <= 0:
                    logger.warning("⏰ CAPTCHA timeout reached")
                    break
                
                logger.info(f"🔄 FAST solve attempt {attempt + 1}/{max_attempts} (remaining: {remaining_time:.1f}s)")
                
                # Приоритет 1: Generic Captcha (быстрый)
                success = await self._solve_generic_captcha_fast(driver, min(self.generic_timeout, remaining_time))
                if success:
                    total_time = time.time() - start_time
                    logger.info(f"✅ CAPTCHA solved by Generic method in {total_time:.1f}s!")
                    return True
                
                # Приоритет 2: Один быстрый API метод (если время осталось)
                remaining_time = self.timeout - (time.time() - start_time)
                if remaining_time > 5:  # Минимум 5 сек для API
                    success = await self._solve_single_api_fast(driver, remaining_time)
                    if success:
                        total_time = time.time() - start_time
                        logger.info(f"✅ CAPTCHA solved by API method in {total_time:.1f}s!")
                        return True
                
                logger.warning(f"❌ Fast solve attempt {attempt + 1} failed")
                
            except Exception as e:
                logger.error(f"❌ CAPTCHA solve attempt {attempt + 1} error: {e}")
                
            # Короткая пауза между попытками
            if attempt < max_attempts - 1:
                await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        logger.error(f"❌ All CAPTCHA solve attempts failed in {total_time:.1f}s")
        return False
    
    async def _quick_detect_captcha(self, driver) -> bool:
        """Быстрое обнаружение капчи (максимум 3 секунды)"""
        try:
            # Сокращенный список самых важных селекторов
            quick_selectors = [
                "//div[contains(@class, 'captcha')]",
                "//iframe[contains(@src, 'recaptcha')]",
                "//div[contains(@class, 'recaptcha')]",
                "//*[contains(@class, 'g-recaptcha')]",
                "//iframe[contains(@src, 'captcha.yandex')]",
                "//*[contains(@id, 'captcha')]"
            ]
            
            for selector in quick_selectors:
                try:
                    # Быстрый поиск без ожидания
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            logger.info(f"🔍 CAPTCHA detected: {selector}")
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Quick CAPTCHA detection error: {e}")
            return False
    
    async def _solve_generic_captcha_fast(self, driver, timeout: float) -> bool:
        """Быстрое решение Generic капчи"""
        try:
            logger.info(f"🎯 Fast Generic CAPTCHA solve (timeout: {timeout:.1f}s)")
            start_time = time.time()
            
            # Быстрый поиск интерактивных элементов капчи
            interactive_selectors = [
                # Кликабельные элементы капчи
                "//div[contains(@class, 'captcha')]//input[@type='checkbox']",
                "//div[contains(@class, 'captcha')]//button",
                "//div[contains(@class, 'captcha')]//div[contains(@class, 'checkbox')]",
                
                # Yandex Smart Captcha checkbox
                "//div[contains(@class, 'CheckboxCaptcha')]//input",
                "//div[contains(@class, 'captcha-checkbox')]//input",
                "//div[contains(@class, 'captcha')]//span[contains(text(), 'not a robot')]",
                
                # Generic clickable captcha areas
                "//*[contains(@class, 'captcha') and @onclick]",
                "//*[contains(@class, 'captcha')]//a",
                "//*[contains(@id, 'captcha')]//input[@type='checkbox']"
            ]
            
            for selector in interactive_selectors:
                try:
                    # Проверяем оставшееся время
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        logger.warning("⏰ Generic captcha timeout")
                        break
                    
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            try:
                                logger.info(f"🎯 Trying to interact with: {selector}")
                                
                                # Прокрутка к элементу
                                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                await asyncio.sleep(0.3)
                                
                                # Попытка клика
                                element.click()
                                await asyncio.sleep(1)
                                
                                # Быстрая проверка исчезновения капчи
                                if not await self._quick_detect_captcha(driver):
                                    solve_time = time.time() - start_time
                                    logger.info(f"✅ Generic captcha solved by click in {solve_time:.1f}s")
                                    return True
                                
                            except Exception as e:
                                logger.debug(f"Element interaction failed: {e}")
                                continue
                                
                except:
                    continue
            
            # Попытка решения через JavaScript (быстрый метод)
            js_success = await self._try_javascript_bypass(driver, timeout - (time.time() - start_time))
            if js_success:
                return True
            
            logger.debug("❌ Fast Generic captcha solve failed")
            return False
            
        except Exception as e:
            logger.debug(f"❌ Generic captcha fast solve error: {e}")
            return False
    
    async def _try_javascript_bypass(self, driver, timeout: float) -> bool:
        """Попытка обхода капчи через JavaScript"""
        try:
            if timeout <= 0:
                return False
                
            logger.info("🔧 Trying JavaScript captcha bypass...")
            
            # Быстрые JS методы обхода
            bypass_scripts = [
                # Скрытие капчи
                """
                var captchas = document.querySelectorAll('[class*="captcha"], [id*="captcha"]');
                captchas.forEach(function(el) {
                    el.style.display = 'none';
                    el.remove();
                });
                return captchas.length > 0;
                """,
                
                # Автоматическое заполнение скрытых полей
                """
                var inputs = document.querySelectorAll('input[name*="captcha"], input[id*="captcha"]');
                inputs.forEach(function(input) {
                    if (input.type === 'hidden') {
                        input.value = 'bypass';
                    }
                });
                return inputs.length > 0;
                """,
                
                # Принудительное выполнение callback'ов
                """
                if (typeof window.onCaptchaSuccess === 'function') {
                    window.onCaptchaSuccess('bypass_token');
                    return true;
                }
                if (typeof window.captchaCallback === 'function') {
                    window.captchaCallback('bypass_token');
                    return true;
                }
                return false;
                """
            ]
            
            for script in bypass_scripts:
                try:
                    result = driver.execute_script(script)
                    if result:
                        await asyncio.sleep(0.5)
                        
                        # Проверка исчезновения капчи
                        if not await self._quick_detect_captcha(driver):
                            logger.info("✅ JavaScript bypass successful")
                            return True
                            
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"JavaScript bypass error: {e}")
            return False
    
    async def _solve_single_api_fast(self, driver, timeout: float) -> bool:
        """Одиночная быстрая попытка через API"""
        try:
            if timeout < 5:  # Минимум 5 секунд для API
                return False
                
            logger.info(f"🔄 Single API solve attempt (timeout: {timeout:.1f}s)")
            
            # Определяем тип капчи для API
            captcha_type = await self._detect_captcha_type_fast(driver)
            
            if captcha_type == 'yandex_smart':
                return await self._solve_yandex_api_fast(driver, timeout)
            elif captcha_type == 'recaptcha':
                return await self._solve_recaptcha_api_fast(driver, timeout)
            else:
                logger.debug("Unknown captcha type for API solve")
                return False
                
        except Exception as e:
            logger.debug(f"Single API solve error: {e}")
            return False
    
    async def _detect_captcha_type_fast(self, driver) -> str:
        """Быстрое определение типа капчи"""
        try:
            # Yandex Smart Captcha
            yandex_selectors = [
                "//iframe[contains(@src, 'captcha.yandex')]",
                "//div[contains(@class, 'CheckboxCaptcha')]"
            ]
            
            for selector in yandex_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if any(el.is_displayed() for el in elements):
                        return 'yandex_smart'
                except:
                    continue
            
            # reCAPTCHA
            recaptcha_selectors = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//div[@class='g-recaptcha']"
            ]
            
            for selector in recaptcha_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if any(el.is_displayed() for el in elements):
                        return 'recaptcha'
                except:
                    continue
            
            return 'unknown'
            
        except:
            return 'unknown'
    
    async def _solve_yandex_api_fast(self, driver, timeout: float) -> bool:
        """Быстрое решение Yandex через API"""
        try:
            # Извлечение site key
            site_key = await self._extract_yandex_site_key_fast(driver)
            if not site_key:
                return False
            
            page_url = driver.current_url
            
            # Быстрая отправка в Anti-Captcha
            if self.provider == 'anti-captcha':
                return await self._anticaptcha_yandex_fast(page_url, site_key, driver, timeout)
            else:
                return await self._2captcha_yandex_fast(page_url, site_key, driver, timeout)
                
        except Exception as e:
            logger.debug(f"Yandex API fast solve error: {e}")
            return False
    
    async def _extract_yandex_site_key_fast(self, driver) -> Optional[str]:
        """Быстрое извлечение Yandex site key"""
        try:
            # Упрощенное извлечение
            script = """
            var iframes = document.querySelectorAll('iframe');
            for (var i = 0; i < iframes.length; i++) {
                var src = iframes[i].src;
                if (src.includes('captcha.yandex') && src.includes('sitekey=')) {
                    return src.split('sitekey=')[1].split('&')[0];
                }
            }
            return null;
            """
            
            result = driver.execute_script(script)
            if result:
                logger.info(f"✅ Found Yandex site key: {result[:20]}...")
                return result
            return None
            
        except:
            return None
    
    async def _anticaptcha_yandex_fast(self, page_url: str, site_key: str, driver, timeout: float) -> bool:
        """Быстрое решение через Anti-Captcha"""
        try:
            task_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "YandexSmartCaptchaTaskProxyless",
                    "websiteURL": page_url,
                    "websiteKey": site_key
                }
            }
            
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                # Отправка задачи
                async with session.post(f"{self.base_url}/createTask", json=task_data) as response:
                    result = await response.json()
                    
                    if result.get('errorId') != 0:
                        logger.error(f"❌ Anti-Captcha task failed: {result.get('errorDescription')}")
                        return False
                    
                    task_id = result.get('taskId')
                
                # Быстрая проверка результата
                while time.time() - start_time < timeout:
                    await asyncio.sleep(3)  # Быстрая проверка каждые 3 сек
                    
                    result_data = {
                        "clientKey": self.api_key,
                        "taskId": task_id
                    }
                    
                    async with session.post(f"{self.base_url}/getTaskResult", json=result_data) as response:
                        result = await response.json()
                        
                        if result.get('status') == 'ready':
                            token = result.get('solution', {}).get('token')
                            if token:
                                return await self._inject_yandex_solution_fast(driver, token)
                        elif result.get('status') != 'processing':
                            break
                
                return False
                
        except Exception as e:
            logger.debug(f"Anti-Captcha Yandex fast error: {e}")
            return False
    
    async def _inject_yandex_solution_fast(self, driver, token: str) -> bool:
        """Быстрая инъекция решения Yandex"""
        try:
            # Быстрые методы инъекции
            scripts = [
                f"if(window.smartCaptcha)window.smartCaptcha.submit('{token}');",
                f"var input=document.querySelector('input[name*=\"captcha\"]');if(input)input.value='{token}';",
                f"if(window.onYandexCaptchaCallback)window.onYandexCaptchaCallback('{token}');"
            ]
            
            for script in scripts:
                try:
                    driver.execute_script(script)
                    await asyncio.sleep(1)
                    
                    if not await self._quick_detect_captcha(driver):
                        logger.info("✅ Yandex solution injected successfully")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Yandex injection error: {e}")
            return False
    
    async def _solve_recaptcha_api_fast(self, driver, timeout: float) -> bool:
        """Быстрое решение reCAPTCHA через API"""
        # Упрощенная реализация для reCAPTCHA
        logger.debug("reCAPTCHA fast solve not implemented")
        return False
    
    async def _2captcha_yandex_fast(self, page_url: str, site_key: str, driver, timeout: float) -> bool:
        """Быстрое решение через 2captcha"""
        try:
            logger.info("🔄 Submitting to 2captcha...")
            
            task_data = {
                'key': self.api_key,
                'method': 'yandex',
                'sitekey': site_key,
                'pageurl': page_url,
                'json': '1'
            }
            
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                # Отправка
                async with session.post("http://2captcha.com/in.php", data=task_data) as response:
                    result = await response.json()
                    
                    if result.get('status') != 1:
                        logger.error(f"❌ 2captcha failed: {result.get('error_text')}")
                        return False
                    
                    task_id = result.get('request')
                
                # Быстрая проверка
                while time.time() - start_time < timeout:
                    await asyncio.sleep(5)
                    
                    params = {
                        'key': self.api_key,
                        'action': 'get',
                        'id': task_id,
                        'json': '1'
                    }
                    
                    async with session.get("http://2captcha.com/res.php", params=params) as response:
                        result = await response.json()
                        
                        if result.get('status') == 1:
                            token = result.get('request')
                            return await self._inject_yandex_solution_fast(driver, token)
                        elif result.get('error_text') != 'CAPCHA_NOT_READY':
                            break
                
                return False
                
        except Exception as e:
            logger.debug(f"2captcha fast error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику решателя капчи"""
        return {
            'enabled': self.enabled,
            'provider': self.provider if self.enabled else None,
            'timeout': self.timeout,
            'max_attempts': self.max_attempts,
            'generic_timeout': self.generic_timeout,
            'optimization': 'fast_generic_priority',
            'status': 'ready' if self.enabled else 'disabled'
        }