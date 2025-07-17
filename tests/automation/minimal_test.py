#!/usr/bin/env python3
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_minimal_chrome():
    """Минимальный тест Chrome"""
    try:
        logger.info("🧪 Testing minimal Chrome setup...")
        
        # Простейшие настройки
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Создаем драйвер
        driver = webdriver.Chrome(options=options)
        
        # Тест навигации
        driver.get("https://httpbin.org/ip")
        
        # Проверяем результат
        if "origin" in driver.page_source.lower():
            logger.info("✅ Minimal Chrome test PASSED!")
            result = True
        else:
            logger.error("❌ Minimal Chrome test FAILED!")
            result = False
        
        driver.quit()
        return result
        
    except Exception as e:
        logger.error(f"❌ Minimal Chrome test error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_minimal_chrome())
    print(f"Test result: {result}")
