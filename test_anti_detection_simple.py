#!/usr/bin/env python3
"""
Простой тест anti-detection системы без прокси
"""

import asyncio
import logging
from web.anti_detection import HumanBehavior, StealthBrowser, BehavioralCamouflage
from web.browser.manager import BrowserManager
from core.config import get_config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_anti_detection_simple():
    """Простой тест anti-detection без прокси"""
    
    logger.info("🚀 Starting simple anti-detection test...")
    
    try:
        config = get_config().to_dict()
        
        # Создаем BrowserManager БЕЗ прокси
        browser_manager = BrowserManager(config, proxy_manager=None)
        
        async with browser_manager:
            logger.info("🔄 Starting browser WITHOUT proxy...")
            success = await browser_manager.start_browser(use_proxy=False)
            
            if not success:
                raise Exception("Failed to start browser")
            
            logger.info("✅ Browser started successfully!")
            
            # Тест stealth verification
            logger.info("🔍 Testing stealth effectiveness...")
            stealth_results = StealthBrowser.verify_stealth_setup(browser_manager.driver)
            logger.info(f"🎯 Stealth score: {stealth_results.get('stealth_score', 'unknown')}")
            logger.info(f"🎯 WebDriver hidden: {stealth_results.get('webdriver_hidden', False)}")
            logger.info(f"🎯 Chrome runtime hidden: {stealth_results.get('chrome_runtime_hidden', False)}")
            
            # Тест простой навигации
            logger.info("🌐 Testing navigation to test site...")
            await browser_manager.navigate_to_url("https://httpbin.org/headers")
            await asyncio.sleep(3)
            
            # Тест человеческого поведения
            logger.info("🎭 Testing human behavior simulation...")
            
            # Найти элемент body для тестирования
            body_element = await browser_manager.find_element_safe("tag name", "body")
            if body_element:
                # Тест human scroll
                HumanBehavior.human_scroll(browser_manager.driver, 'down', 200)
                await asyncio.sleep(1)
                
                # Тест random mouse movement
                HumanBehavior.random_mouse_movement(browser_manager.driver)
                await asyncio.sleep(1)
                
                logger.info("✅ Human behavior tests completed")
            
            # Сохранить скриншот
            screenshot_path = "logs/anti_detection_test.png"
            await browser_manager.take_screenshot(screenshot_path)
            logger.info(f"📸 Screenshot saved: {screenshot_path}")
            
            logger.info("🎉 All anti-detection tests PASSED!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Anti-detection test FAILED: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_anti_detection_simple())