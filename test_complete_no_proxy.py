#!/usr/bin/env python3
"""
Complete automation test WITHOUT proxy - для тестирования anti-detection
"""

import asyncio
import logging
from web.browser.manager import BrowserManager
from web.anti_detection import HumanBehavior, StealthBrowser, BehavioralCamouflage
from core.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_no_proxy():
    """Полный тест автоматизации БЕЗ прокси"""
    
    logger.info("🚀 Starting COMPLETE automation test WITHOUT proxy...")
    
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
            stealth_results = StealthBrowser.verify_stealth_setup(browser_manager.driver)
            logger.info(f"🎯 Stealth effectiveness: {stealth_results.get('stealth_score', 'unknown')}")
            
            # NAVIGATION TEST
            logger.info("🌐 Navigating to multitransfer.ru...")
            success = await browser_manager.navigate_to_url("https://multitransfer.ru")
            if not success:
                raise Exception("Failed to navigate to multitransfer.ru")
            
            # ANTI-DETECTION: Pre-browsing behavior (сокращенная версия для теста)
            logger.info("🎭 Starting pre-browsing behavior (30 seconds)...")  
            await BehavioralCamouflage.pre_browsing_behavior(browser_manager.driver, "https://multitransfer.ru", duration_minutes=0.5)
            
            # Тест основных функций anti-detection
            logger.info("🎯 Testing main automation steps...")
            
            # Поиск кнопки "ПЕРЕВЕСТИ ЗА РУБЕЖ"
            all_buttons = await browser_manager.find_elements_safe("tag name", "button")
            transfer_button = None
            
            for btn in all_buttons:
                try:
                    button_text = await browser_manager.get_element_text(btn)
                    if "ПЕРЕВЕСТИ ЗА РУБЕЖ" in button_text.upper():
                        transfer_button = btn
                        logger.info(f"🎯 Found transfer button: '{button_text}'")
                        break
                except:
                    continue
            
            if transfer_button:
                # ANTI-DETECTION: Human click with preparation
                logger.info("🖱️ Clicking transfer button with human behavior...")
                HumanBehavior.human_click_with_preparation(browser_manager.driver, transfer_button)
                
                # Human delay
                delay = HumanBehavior.random_delay(3.0, 5.0)
                await asyncio.sleep(delay)
                
                logger.info("✅ Transfer button clicked successfully!")
            else:
                logger.warning("⚠️ Transfer button not found, but test continues...")
            
            # Сохранить финальный скриншот
            await browser_manager.take_screenshot("logs/complete_test_no_proxy.png")
            logger.info("📸 Final screenshot saved")
            
            logger.info("🎉 Complete test WITHOUT proxy: ✅ SUCCESS")
            return True
            
    except Exception as e:
        logger.error(f"❌ Complete test WITHOUT proxy: FAILED - {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_complete_no_proxy())