#!/usr/bin/env python3
"""
Simple browser test without config dependencies
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from web.browser.manager import BrowserManager
from selenium.webdriver.common.by import By

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Минимальная конфигурация для тестирования
def get_test_config():
    """Простая конфигурация для тестирования"""
    return {
        'browser': {
            'headless': True,
            'window_size': '1920,1080',
            'page_load_timeout': 30,
            'implicit_wait': 10,
            'user_agents': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ]
        }
    }

async def test_basic_browser():
    """Тест базового запуска браузера"""
    logger.info("🧪 Testing basic browser functionality...")
    
    try:
        # Простая конфигурация
        config = get_test_config()
        
        # Создаем браузер менеджер БЕЗ прокси
        browser_manager = BrowserManager(config, proxy_manager=None)
        
        async with browser_manager:
            # Запускаем браузер в прямом режиме
            success = await browser_manager.start_browser(use_proxy=False)
            if not success:
                logger.error("❌ Failed to start browser")
                return False
            
            # Переходим на тестовый сайт
            logger.info("🌐 Testing navigation to httpbin.org...")
            success = await browser_manager.navigate_to_url("https://httpbin.org/ip")
            if not success:
                logger.error("❌ Failed to navigate to httpbin.org")
                return False
            
            # Проверяем содержимое
            page_source = await browser_manager.get_page_source()
            if "origin" in page_source.lower():
                logger.info("✅ Browser navigation works!")
                return True
            else:
                logger.error("❌ Navigation failed - no expected content")
                return False
            
    except Exception as e:
        logger.error(f"❌ Browser test failed: {e}")
        return False

async def test_multitransfer_site():
    """Тест доступа к multitransfer.ru"""
    logger.info("🧪 Testing MultiTransfer site access...")
    
    try:
        config = get_test_config()
        browser_manager = BrowserManager(config, proxy_manager=None)
        
        async with browser_manager:
            success = await browser_manager.start_browser(use_proxy=False)
            if not success:
                return False
            
            # Тестируем доступ к сайту
            logger.info("🌐 Navigating to multitransfer.ru...")
            success = await browser_manager.navigate_to_url("https://multitransfer.ru")
            
            if success:
                logger.info("✅ Successfully reached multitransfer.ru")
                
                # Ждем загрузки
                await asyncio.sleep(5)
                
                # Ищем основные элементы
                logger.info("�� Searching for form elements...")
                
                # Поиск полей ввода
                amount_elements = await browser_manager.find_elements_safe(
                    By.XPATH, 
                    "//input[@type='text' or @type='number']"
                )
                logger.info(f"💰 Found {len(amount_elements)} input fields")
                
                # Поиск всех кнопок
                buttons = await browser_manager.find_elements_safe(
                    By.XPATH, 
                    "//button"
                )
                logger.info(f"🔘 Found {len(buttons)} buttons")
                
                # Делаем скриншот
                await browser_manager.take_screenshot("multitransfer_page.png")
                logger.info("📸 Screenshot saved as multitransfer_page.png")
                
                return True
            else:
                logger.error("❌ Failed to reach multitransfer.ru")
                return False
                
    except Exception as e:
        logger.error(f"❌ MultiTransfer site test failed: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    logger.info("🚀 Starting simplified browser tests...")
    
    # Тест 1: Базовый браузер
    test1_result = await test_basic_browser()
    logger.info(f"📊 Basic browser test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    
    # Тест 2: Доступ к MultiTransfer
    test2_result = await test_multitransfer_site()
    logger.info(f"📊 MultiTransfer site test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        logger.info("🎉 ALL TESTS PASSED - Ready for automation!")
        logger.info("📋 Next steps:")
        logger.info("   1. Browser works correctly")
        logger.info("   2. Can access multitransfer.ru")
        logger.info("   3. Form elements are detectable")
        logger.info("   4. Ready to implement form automation")
        return True
    else:
        logger.error("💥 SOME TESTS FAILED - Need investigation")
        return False

if __name__ == "__main__":
    asyncio.run(main())
