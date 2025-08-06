"""
Behavioral Camouflage Module - Имитация естественного поведения пользователя
Включает pre-browsing, человеческие ошибки, изучение страницы
"""

import random
import time
import logging
from typing import List, Optional, Any, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)

class BehavioralCamouflage:
    """Модуль для имитации естественного поведения пользователя"""
    
    # Константы поведения
    EXPLORATION_MIN_TIME = 3.0    # Минимальное время изучения
    EXPLORATION_MAX_TIME = 7.0    # Максимальное время изучения
    HESITATION_PROBABILITY = 0.4  # 40% шанс на раздумья
    TAB_USAGE_PROBABILITY = 0.3   # 30% шанс использовать Tab
    WRONG_CLICK_PROBABILITY = 0.15 # 15% шанс кликнуть не туда
    
    @staticmethod
    async def pre_browsing_behavior(driver, base_url: str, duration_minutes: float = 1.0) -> None:
        """
        Поведение до основных действий - изучение сайта как реальный пользователь
        
        Args:
            driver: WebDriver
            base_url: Базовый URL сайта
            duration_minutes: Продолжительность изучения в минутах
        """
        logger.info(f"🎭 Starting pre-browsing behavior for {duration_minutes:.1f} minutes")
        
        try:
            # 1. Посетить главную страницу
            logger.info("📖 Visiting homepage and reading...")
            driver.get(base_url)
            
            # Ждем загрузки и "читаем" содержимое
            initial_reading_time = random.uniform(3, 7)
            logger.debug(f"⏳ Initial page reading: {initial_reading_time:.1f}s")
            time.sleep(initial_reading_time)
            
            # 2. Естественная прокрутка страницы (изучение)
            await BehavioralCamouflage._explore_page_content(driver)
            
            # 3. Попытка взаимодействия с навигацией
            await BehavioralCamouflage._explore_navigation_menu(driver)
            
            # 4. Случайные действия пользователя
            await BehavioralCamouflage._perform_random_user_actions(driver, duration_minutes)
            
            # 5. Вернуться на главную (если ушли)
            current_url = driver.current_url
            if base_url not in current_url:
                logger.debug("🔙 Returning to homepage")
                driver.get(base_url)
                time.sleep(random.uniform(2, 4))
            
            logger.info("✅ Pre-browsing behavior completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Pre-browsing behavior partially failed: {e}")
            # Минимальная задержка даже при ошибке
            time.sleep(random.uniform(5, 10))
    
    @staticmethod
    async def _explore_page_content(driver) -> None:
        """Изучение содержимого страницы прокруткой"""
        try:
            # Получаем высоту страницы
            total_height = driver.execute_script("return document.body.scrollHeight")
            current_scroll = 0
            
            # Прокручиваем по частям (имитируем чтение)
            scroll_steps = random.randint(3, 6)
            step_size = total_height // scroll_steps
            
            for i in range(scroll_steps):
                # Прокрутка вниз
                scroll_to = min(current_scroll + step_size + random.randint(-50, 100), total_height)
                driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                current_scroll = scroll_to
                
                # Пауза для "чтения"
                reading_time = random.uniform(1.5, 4.0)
                logger.debug(f"📜 Reading section {i+1}/{scroll_steps} for {reading_time:.1f}s")
                time.sleep(reading_time)
                
                # Иногда прокручиваем немного назад (как при перечитывании)
                if random.random() < 0.3:
                    back_scroll = random.randint(50, 150)
                    driver.execute_script(f"window.scrollBy(0, -{back_scroll});")
                    time.sleep(random.uniform(0.5, 1.5))
                    driver.execute_script(f"window.scrollBy(0, {back_scroll});")
            
            # Прокрутка обратно наверх
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.debug(f"Page exploration failed: {e}")
    
    @staticmethod
    async def _explore_navigation_menu(driver) -> None:
        """Изучение навигационного меню"""
        try:
            # Ищем элементы навигации
            nav_selectors = [
                "nav a", "header a", ".menu a", ".navbar a", 
                "ul.menu li a", ".nav-link", "[role='navigation'] a"
            ]
            
            menu_items = []
            for selector in nav_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    menu_items.extend(elements[:5])  # Максимум 5 элементов
                    if len(menu_items) >= 3:  # Достаточно для изучения
                        break
                except:
                    continue
            
            if menu_items:
                # Случайно наводимся на 1-3 элемента меню
                items_to_explore = random.sample(menu_items, min(len(menu_items), random.randint(1, 3)))
                
                for item in items_to_explore:
                    try:
                        # Наводим мышь на элемент
                        ActionChains(driver).move_to_element(item).pause(
                            random.uniform(0.8, 2.0)
                        ).perform()
                        
                        logger.debug(f"🖱️ Hovering over menu item: {item.text[:30]}")
                        time.sleep(random.uniform(0.5, 1.5))
                        
                        # Иногда кликаем (но редко)
                        if random.random() < 0.1:  # 10% шанс
                            logger.debug("🔍 Exploring menu link")
                            item.click()
                            time.sleep(random.uniform(2, 5))
                            driver.back()  # Возвращаемся
                            time.sleep(random.uniform(1, 3))
                            break  # Один переход достаточно
                            
                    except Exception as e:
                        logger.debug(f"Menu exploration error: {e}")
                        continue
            
        except Exception as e:
            logger.debug(f"Navigation exploration failed: {e}")
    
    @staticmethod
    async def _perform_random_user_actions(driver, duration_minutes: float) -> None:
        """Случайные действия пользователя"""
        end_time = time.time() + (duration_minutes * 60)
        
        actions = [
            'scroll_random', 'move_mouse', 'pause_reading', 
            'mini_scroll', 'hover_element', 'nothing'
        ]
        
        while time.time() < end_time:
            action = random.choice(actions)
            
            try:
                if action == 'scroll_random':
                    direction = random.choice(['up', 'down'])
                    pixels = random.randint(100, 400)
                    if direction == 'down':
                        driver.execute_script(f"window.scrollBy(0, {pixels});")
                    else:
                        driver.execute_script(f"window.scrollBy(0, -{pixels});")
                
                elif action == 'move_mouse':
                    # Случайное движение мыши
                    try:
                        body = driver.find_element(By.TAG_NAME, "body")
                        ActionChains(driver).move_to_element_with_offset(
                            body, random.randint(100, 800), random.randint(100, 600)
                        ).perform()
                    except:
                        pass
                
                elif action == 'pause_reading':
                    # Длинная пауза (как при чтении)
                    time.sleep(random.uniform(3, 8))
                
                elif action == 'mini_scroll':
                    # Небольшая прокрутка
                    driver.execute_script(f"window.scrollBy(0, {random.randint(50, 150)});")
                
                elif action == 'hover_element':
                    # Наведение на случайный элемент
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, "div, p, span, a")
                        if elements:
                            element = random.choice(elements[:10])
                            ActionChains(driver).move_to_element(element).pause(
                                random.uniform(0.5, 2.0)
                            ).perform()
                    except:
                        pass
                
                # Базовая пауза между действиями
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.debug(f"Random action '{action}' failed: {e}")
                time.sleep(random.uniform(1, 3))
    
    @staticmethod
    def simulate_field_selection_hesitation(driver, field_elements: List[WebElement]) -> WebElement:
        """
        Имитация раздумий при выборе полей
        
        Args:
            driver: WebDriver
            field_elements: Список элементов для выбора
            
        Returns:
            WebElement: Выбранный элемент
        """
        if len(field_elements) <= 1 or random.random() > BehavioralCamouflage.HESITATION_PROBABILITY:
            return field_elements[-1] if field_elements else None
        
        logger.debug("🤔 Simulating field selection hesitation")
        
        try:
            # "Случайно" наведемся на неправильное поле
            wrong_field = random.choice(field_elements[:-1])
            
            # Прокрутка к неправильному полю
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", wrong_field)
            time.sleep(random.uniform(0.5, 1.0))
            
            # Наведение мыши на неправильное поле
            ActionChains(driver).move_to_element(wrong_field).pause(
                random.uniform(1.0, 2.5)
            ).perform()
            
            logger.debug("⏳ Hesitation pause")
            time.sleep(random.uniform(0.8, 2.0))
            
            # Теперь переходим к правильному полю
            correct_field = field_elements[-1]
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", correct_field)
            time.sleep(random.uniform(0.3, 0.8))
            
            return correct_field
            
        except Exception as e:
            logger.debug(f"Hesitation simulation failed: {e}")
            return field_elements[-1] if field_elements else None
    
    @staticmethod
    def simulate_reading(driver, element: WebElement) -> None:
        """
        Имитация чтения элемента
        
        Args:
            driver: WebDriver
            element: Элемент для чтения
        """
        try:
            # Прокрутка к элементу
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(random.uniform(0.5, 1.0))
            
            # Определяем время чтения по содержимому
            try:
                text_length = len(element.text.strip())
                # Базовое время: 50ms на символ, минимум 1 сек, максимум 8 сек
                reading_time = min(max(text_length * 0.05, 1.0), 8.0)
                
                # Добавляем случайность
                reading_time += random.uniform(-0.5, 1.5)
                reading_time = max(reading_time, 0.5)
                
                logger.debug(f"📖 Reading element ({text_length} chars) for {reading_time:.1f}s")
                
            except:
                reading_time = random.uniform(1.5, 4.0)
            
            time.sleep(reading_time)
            
        except Exception as e:
            logger.debug(f"Reading simulation failed: {e}")
            time.sleep(random.uniform(1, 3))
    
    @staticmethod
    def random_tab_usage(driver, target_field: WebElement = None) -> bool:
        """
        Случайное использование Tab для навигации
        
        Args:
            driver: WebDriver
            target_field: Целевое поле (опционально)
            
        Returns:
            bool: True если использовали Tab
        """
        if random.random() > BehavioralCamouflage.TAB_USAGE_PROBABILITY:
            return False
        
        logger.debug("⌨️ Using Tab navigation")
        
        try:
            # Получаем текущий активный элемент
            current_element = driver.switch_to.active_element
            
            # Используем Tab 1-3 раза
            tab_count = random.randint(1, 3)
            for _ in range(tab_count):
                current_element.send_keys(Keys.TAB)
                time.sleep(random.uniform(0.3, 0.8))
                current_element = driver.switch_to.active_element
            
            return True
            
        except Exception as e:
            logger.debug(f"Tab navigation failed: {e}")
            return False
    
    @staticmethod
    def simulate_uncertainty(driver) -> None:
        """
        Имитация неуверенности - случайные движения и действия
        
        Args:
            driver: WebDriver
        """
        logger.debug("😕 Simulating user uncertainty")
        
        uncertainty_actions = [
            'scroll_back_forth', 'mouse_wander', 'pause_long', 'mini_refresh'
        ]
        
        action = random.choice(uncertainty_actions)
        
        try:
            if action == 'scroll_back_forth':
                # Прокрутка туда-сюда
                pixels = random.randint(150, 400)
                driver.execute_script(f"window.scrollBy(0, {pixels});")
                time.sleep(random.uniform(1.0, 2.5))
                driver.execute_script(f"window.scrollBy(0, -{pixels});")
                time.sleep(random.uniform(0.5, 1.5))
                
            elif action == 'mouse_wander':
                # Бесцельное движение мыши
                try:
                    for _ in range(random.randint(2, 5)):
                        x = random.randint(100, 1000)
                        y = random.randint(100, 600)
                        ActionChains(driver).move_by_offset(x, y).pause(
                            random.uniform(0.3, 0.8)
                        ).perform()
                except:
                    pass
                    
            elif action == 'pause_long':
                # Долгая пауза (как при раздумьях)
                pause_time = random.uniform(3.0, 7.0)
                logger.debug(f"🤔 Long uncertainty pause: {pause_time:.1f}s")
                time.sleep(pause_time)
                
            elif action == 'mini_refresh':
                # Небольшое обновление (F5 иногда)
                if random.random() < 0.1:  # 10% шанс
                    logger.debug("🔄 Mini refresh (F5)")
                    driver.refresh()
                    time.sleep(random.uniform(2, 5))
                    
        except Exception as e:
            logger.debug(f"Uncertainty simulation failed: {e}")
    
    @staticmethod
    def simulate_wrong_click(driver, correct_element: WebElement, nearby_elements: List[WebElement] = None) -> bool:
        """
        Имитация случайного неправильного клика
        
        Args:
            driver: WebDriver
            correct_element: Правильный элемент
            nearby_elements: Близлежащие элементы для ошибочного клика
            
        Returns:
            bool: True если произошла ошибка клика
        """
        if random.random() > BehavioralCamouflage.WRONG_CLICK_PROBABILITY:
            return False
        
        logger.debug("❌ Simulating wrong click")
        
        try:
            # Если есть близлежащие элементы, кликаем на один из них
            if nearby_elements:
                wrong_element = random.choice(nearby_elements)
                try:
                    wrong_element.click()
                    logger.debug("🔄 Clicked wrong element, correcting...")
                    
                    # Пауза осознания ошибки
                    time.sleep(random.uniform(1.0, 2.5))
                    
                    # Теперь кликаем правильный
                    correct_element.click()
                    return True
                    
                except:
                    # Если клик по неправильному элементу не удался, кликаем по правильному
                    correct_element.click()
                    return False
            else:
                # Кликаем рядом с правильным элементом (промах)
                try:
                    offset_x = random.randint(-30, 30)
                    offset_y = random.randint(-20, 20)
                    
                    ActionChains(driver).move_to_element_with_offset(
                        correct_element, offset_x, offset_y
                    ).click().perform()
                    
                    # Пауза
                    time.sleep(random.uniform(0.8, 1.5))
                    
                    # Правильный клик
                    correct_element.click()
                    return True
                    
                except:
                    correct_element.click()
                    return False
                    
        except Exception as e:
            logger.debug(f"Wrong click simulation failed: {e}")
            try:
                correct_element.click()
            except:
                pass
            return False
    
    @staticmethod
    def natural_form_filling_order(form_fields: List[Tuple[str, WebElement]]) -> List[Tuple[str, WebElement]]:
        """
        Естественный порядок заполнения полей формы (не всегда сверху вниз)
        
        Args:
            form_fields: Список кортежей (название_поля, элемент)
            
        Returns:
            List: Переупорядоченный список полей
        """
        if len(form_fields) <= 2:
            return form_fields
        
        # 70% шанс заполнять в обычном порядке
        if random.random() < 0.7:
            return form_fields
        
        logger.debug("🔀 Using natural form filling order")
        
        # Иногда меняем порядок (но логично)
        reordered = form_fields.copy()
        
        # Можем поменять местами соседние поля
        if len(reordered) >= 3:
            swap_idx = random.randint(0, len(reordered) - 2)
            if random.random() < 0.3:  # 30% шанс
                reordered[swap_idx], reordered[swap_idx + 1] = reordered[swap_idx + 1], reordered[swap_idx]
        
        return reordered
    
    @staticmethod
    def add_focus_unfocus_events(driver, element: WebElement) -> None:
        """
        Добавление событий фокуса/потери фокуса (имитация отвлечения)
        
        Args:
            driver: WebDriver
            element: Элемент для манипуляций с фокусом
        """
        if random.random() < 0.2:  # 20% шанс
            logger.debug("👁️ Adding focus/unfocus events")
            
            try:
                # Фокус на элемент
                element.click()
                time.sleep(random.uniform(0.3, 0.8))
                
                # Убираем фокус (кликаем в сторону)
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    ActionChains(driver).move_to_element_with_offset(
                        body, random.randint(50, 200), random.randint(50, 200)
                    ).click().perform()
                    
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    # Возвращаем фокус
                    element.click()
                    
                except:
                    pass
                    
            except Exception as e:
                logger.debug(f"Focus/unfocus simulation failed: {e}")
    
    @staticmethod
    def simulate_page_leave_return(driver, probability: float = 0.05) -> bool:
        """
        Имитация случайного ухода со страницы и возвращения
        
        Args:
            driver: WebDriver
            probability: Вероятность срабатывания (по умолчанию 5%)
            
        Returns:
            bool: True если произошло переключение
        """
        if random.random() > probability:
            return False
        
        logger.debug("🔄 Simulating page leave/return")
        
        try:
            # Запоминаем текущий URL
            original_url = driver.current_url
            
            # Имитируем переключение на другую вкладку (открыть новую вкладку)
            driver.execute_script("window.open('about:blank', '_blank');")
            
            # Переключаемся на новую вкладку
            driver.switch_to.window(driver.window_handles[-1])
            
            # Небольшая пауза
            time.sleep(random.uniform(2, 5))
            
            # Закрываем вкладку и возвращаемся
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            
            # Дополнительная пауза
            time.sleep(random.uniform(1, 3))
            
            return True
            
        except Exception as e:
            logger.debug(f"Page leave/return failed: {e}")
            return False