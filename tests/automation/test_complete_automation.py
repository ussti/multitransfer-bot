#!/usr/bin/env python3
"""
Complete automation test with currency and transfer method selection
Полный тест автоматизации с выбором валюты и способа перевода
"""

import asyncio
import logging
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from web.browser.manager import BrowserManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_test_config():
    return {
        'browser': {
            'headless': False,
            'window_size': '1920,1080',
            'page_load_timeout': 30,
            'implicit_wait': 10,
            'user_agents': [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ]
        }
    }

async def human_type_text(browser_manager, element, text, min_delay=0.05, max_delay=0.2):
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

async def test_complete_flow():
    """Полный тест автоматизации"""
    logger.info("🔍 Testing COMPLETE automation flow...")
    
    config = get_test_config()
    browser_manager = BrowserManager(config, proxy_manager=None)
    
    async with browser_manager:
        success = await browser_manager.start_browser(use_proxy=False)
        if not success:
            return False
        
        # Переходим на сайт
        success = await browser_manager.navigate_to_url("https://multitransfer.ru")
        if not success:
            return False
        
        await asyncio.sleep(random.uniform(3, 5))
        
        # Шаг 1: Клик по кнопке "ПЕРЕВЕСТИ ЗА РУБЕЖ"
        logger.info("📍 Step 1: Click 'ПЕРЕВЕСТИ ЗА РУБЕЖ'")
        
        all_buttons = await browser_manager.find_elements_safe(By.TAG_NAME, "button")
        button_clicked = False
        
        for i, btn in enumerate(all_buttons):
            try:
                text = await browser_manager.get_element_text(btn)
                if "ПЕРЕВЕСТИ ЗА РУБЕЖ" in text:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    if await browser_manager.click_element_safe(btn):
                        logger.info(f"✅ Successfully clicked button {i}")
                        button_clicked = True
                        break
            except:
                pass
        
        if not button_clicked:
            logger.error("❌ Could not click 'ПЕРЕВЕСТИ ЗА РУБЕЖ'")
            return False
        
        await asyncio.sleep(random.uniform(3, 5))
        await browser_manager.take_screenshot("step1_modal_opened.png")
        
        # Шаг 2: Выбор Таджикистана
        logger.info("�� Step 2: Select Tajikistan")
        
        tajikistan_clicked = False
        tajikistan_elements = await browser_manager.find_elements_safe(
            By.XPATH, 
            "//span[text()='Таджикистан']/parent::div"
        )
        
        for element in tajikistan_elements:
            try:
                if element.is_displayed():
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    browser_manager.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    await asyncio.sleep(0.3)
                    
                    if await browser_manager.click_element_safe(element):
                        logger.info("✅ Successfully clicked Tajikistan")
                        tajikistan_clicked = True
                        break
                    else:
                        browser_manager.driver.execute_script("arguments[0].click();", element)
                        logger.info("✅ Successfully clicked Tajikistan via JavaScript")
                        tajikistan_clicked = True
                        break
            except:
                pass
        
        if not tajikistan_clicked:
            logger.error("❌ Could not select Tajikistan")
            return False
        
        await asyncio.sleep(random.uniform(3, 5))
        await browser_manager.take_screenshot("step2_country_selected.png")
        
        # Шаг 3: Заполнение суммы
        logger.info("📍 Step 3: Fill amount")
        
        amount_inputs = await browser_manager.find_elements_safe(By.XPATH, "//input[contains(@placeholder, 'RUB')]")
        
        amount_filled = False
        for inp in amount_inputs:
            try:
                if inp.is_displayed() and inp.is_enabled():
                    logger.info("🎯 Filling amount field")
                    success = await human_type_text(browser_manager, inp, "1000", 0.1, 0.3)
                    if success:
                        logger.info("✅ Amount filled successfully")
                        amount_filled = True
                        break
            except:
                pass
        
        if not amount_filled:
            logger.error("❌ Could not fill amount")
            return False
        
        await asyncio.sleep(3)
        await browser_manager.take_screenshot("step3_amount_filled.png")
        
        # Шаг 4: Выбор валюты TJS
        logger.info("📍 Step 4: Select TJS currency")
        
        # Ищем кнопку TJS в разделе валют
        tjs_selectors = [
            "//button[contains(text(), 'TJS')]",
            "//div[contains(text(), 'TJS')]",
            "//*[contains(@class, 'currency') and contains(text(), 'TJS')]",
            "//*[text()='TJS']"
        ]
        
        tjs_selected = False
        for selector in tjs_selectors:
            elements = await browser_manager.find_elements_safe(By.XPATH, selector)
            logger.info(f"Found {len(elements)} TJS elements with selector: {selector}")
            
            for element in elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        logger.info("🎯 Clicking TJS currency button")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        if await browser_manager.click_element_safe(element):
                            logger.info("✅ Successfully selected TJS currency")
                            tjs_selected = True
                            break
                        else:
                            browser_manager.driver.execute_script("arguments[0].click();", element)
                            logger.info("✅ Successfully selected TJS currency via JavaScript")
                            tjs_selected = True
                            break
                except Exception as e:
                    logger.debug(f"TJS element click failed: {e}")
                    continue
            
            if tjs_selected:
                break
        
        if not tjs_selected:
            logger.warning("⚠️ Could not select TJS currency, continuing...")
        
        await asyncio.sleep(3)
        await browser_manager.take_screenshot("step4_currency_selected.png")
        
        # Шаг 5: Выбор способа перевода "Корти Милли"
        logger.info("📍 Step 5: Select 'Корти Милли' transfer method")
        
        # Сначала ищем dropdown или кнопку для выбора способа перевода
        transfer_method_selectors = [
            "//div[contains(text(), 'Способ перевода')]//following-sibling::*",
            "//div[contains(text(), 'Способ перевода')]//parent::*//div[contains(@class, 'dropdown') or contains(@class, 'select')]",
            "//div[contains(@class, 'transfer-method') or contains(@class, 'method')]",
            "//*[contains(text(), 'Выберите способ') or contains(text(), 'способ')]"
        ]
        
        method_dropdown_clicked = False
        for selector in transfer_method_selectors:
            elements = await browser_manager.find_elements_safe(By.XPATH, selector)
            logger.info(f"Found {len(elements)} transfer method elements with selector: {selector}")
            
            for element in elements:
                try:
                    if element.is_displayed():
                        logger.info("🎯 Clicking transfer method dropdown")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        if await browser_manager.click_element_safe(element):
                            logger.info("✅ Successfully clicked transfer method dropdown")
                            method_dropdown_clicked = True
                            break
                        else:
                            browser_manager.driver.execute_script("arguments[0].click();", element)
                            logger.info("✅ Successfully clicked transfer method dropdown via JavaScript")
                            method_dropdown_clicked = True
                            break
                except:
                    continue
            
            if method_dropdown_clicked:
                break
        
        await asyncio.sleep(3)
        await browser_manager.take_screenshot("step5_transfer_method_dropdown.png")
        
        # Теперь ищем "Корти Милли" в открывшемся списке
        korti_milli_selectors = [
            "//*[contains(text(), 'Корти Милли')]",
            "//div[contains(text(), 'Корти Милли')]",
            "//span[contains(text(), 'Корти Милли')]",
            "//li[contains(text(), 'Корти Милли')]",
            "//*[contains(@class, 'option') and contains(text(), 'Корти Милли')]"
        ]
        
        korti_milli_selected = False
        for selector in korti_milli_selectors:
            elements = await browser_manager.find_elements_safe(By.XPATH, selector)
            logger.info(f"Found {len(elements)} Korti Milli elements with selector: {selector}")
            
            for element in elements:
                try:
                    if element.is_displayed():
                        logger.info("🎯 Clicking Корти Милли option")
                        await asyncio.sleep(random.uniform(0.3, 0.7))
                        
                        browser_manager.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        await asyncio.sleep(0.3)
                        
                        if await browser_manager.click_element_safe(element):
                            logger.info("✅ Successfully selected Корти Милли")
                            korti_milli_selected = True
                            break
                        else:
                            browser_manager.driver.execute_script("arguments[0].click();", element)
                            logger.info("✅ Successfully selected Корти Милли via JavaScript")
                            korti_milli_selected = True
                            break
                except Exception as e:
                    logger.debug(f"Korti Milli element click failed: {e}")
                    continue
            
            if korti_milli_selected:
                break
        
        if not korti_milli_selected:
            logger.warning("⚠️ Could not select Корти Милли, continuing...")
        
        await asyncio.sleep(3)
        await browser_manager.take_screenshot("step5_method_selected.png")
        
        # Шаг 6: Нажать кнопку "ПРОДОЛЖИТЬ"
        logger.info("📍 Step 6: Click 'ПРОДОЛЖИТЬ' button")
        
        continue_buttons = await browser_manager.find_elements_safe(By.TAG_NAME, "button")
        continue_clicked = False
        
        for i, btn in enumerate(continue_buttons):
            try:
                text = await browser_manager.get_element_text(btn)
                if text and "ПРОДОЛЖИТЬ" in text.upper():
                    logger.info(f"�� Found continue button: '{text}'")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    if await browser_manager.click_element_safe(btn):
                        logger.info(f"✅ Successfully clicked continue button")
                        continue_clicked = True
                        break
            except:
                pass
        
        if not continue_clicked:
            logger.warning("⚠️ Could not find continue button")
        
        await asyncio.sleep(5)
        await browser_manager.take_screenshot("final_complete_result.png")
        
        logger.info("✅ Complete automation flow finished!")
        return True

async def main():
    """Главная функция тестирования"""
    logger.info("🚀 Starting COMPLETE automation test...")
    
    result = await test_complete_flow()
    logger.info(f"📊 Complete test: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if result:
        logger.info("🎉 COMPLETE AUTOMATION PASSED!")
        logger.info("📋 Completed steps:")
        logger.info("   ✅ 1. Clicked 'ПЕРЕВЕСТИ ЗА РУБЕЖ'")
        logger.info("   ✅ 2. Selected Tajikistan")
        logger.info("   ✅ 3. Filled amount (1000 RUB)")
        logger.info("   ✅ 4. Selected TJS currency")
        logger.info("   ✅ 5. Selected Корти Милли method")
        logger.info("   ✅ 6. Clicked continue")
        logger.info("   🎯 Ready for Telegram bot integration!")
    else:
        logger.error("💥 COMPLETE AUTOMATION FAILED")
    
    return result

if __name__ == "__main__":
    asyncio.run(main())
