"""
Humanization Module - Эмуляция человеческого поведения
Включает случайные задержки, вариативную печать, человеческие ошибки
"""

import random
import time
import logging
from typing import Tuple, List, Optional
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

class HumanBehavior:
    """Модуль для эмуляции человеческого поведения"""
    
    # Константы для настройки поведения
    MIN_STEP_DELAY = 5.0    # Минимальная задержка между шагами
    MAX_STEP_DELAY = 15.0   # Максимальная задержка между шагами
    MIN_TYPING_DELAY = 0.15 # Минимальная задержка между символами (150ms)
    MAX_TYPING_DELAY = 0.4  # Максимальная задержка между символами (400ms)
    MISTAKE_PROBABILITY = 0.1  # 10% шанс на ошибку
    
    @staticmethod
    def random_delay(min_sec: float = None, max_sec: float = None) -> float:
        """
        Случайная задержка между действиями
        
        Args:
            min_sec: Минимальная задержка (по умолчанию 5-15 сек)
            max_sec: Максимальная задержка
            
        Returns:
            float: Время задержки в секундах
        """
        min_sec = min_sec or HumanBehavior.MIN_STEP_DELAY
        max_sec = max_sec or HumanBehavior.MAX_STEP_DELAY
        
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"⏳ Human delay: {delay:.2f}s")
        return delay
    
    @staticmethod
    def typing_delay() -> float:
        """
        Случайная задержка между символами при печати
        
        Returns:
            float: Время задержки в секундах (150-400ms)
        """
        return random.uniform(HumanBehavior.MIN_TYPING_DELAY, HumanBehavior.MAX_TYPING_DELAY)
    
    @staticmethod
    def word_pause() -> float:
        """
        Пауза между словами (более длинная чем между символами)
        
        Returns:
            float: Время паузы в секундах (300-800ms)
        """
        return random.uniform(0.3, 0.8)
    
    @staticmethod
    def reading_pause() -> float:
        """
        Пауза для 'чтения' содержимого
        
        Returns:
            float: Время паузы в секундах (2-5 сек)
        """
        return random.uniform(2.0, 5.0)
    
    @staticmethod
    def should_make_mistake() -> bool:
        """
        Определяет, нужно ли сделать ошибку при вводе
        
        Returns:
            bool: True если нужно сделать ошибку (10% шанс)
        """
        return random.random() < HumanBehavior.MISTAKE_PROBABILITY
    
    @staticmethod
    def human_type(element: WebElement, text: str, driver=None) -> None:
        """
        Человекоподобная печать с возможными ошибками и исправлениями
        
        Args:
            element: Веб-элемент для ввода текста
            text: Текст для ввода
            driver: WebDriver (опционально, для логирования)
        """
        logger.info(f"🖊️ Human typing: '{text[:10]}{'...' if len(text) > 10 else ''}'")
        
        # Очищаем поле
        element.clear()
        time.sleep(random.uniform(0.1, 0.3))
        
        # 10% шанс на ошибку в начале
        if HumanBehavior.should_make_mistake():
            logger.debug("🔄 Making intentional typing mistake")
            
            # Набираем неправильный символ
            wrong_chars = 'qwertyuiopasdfghjklzxcvbnm'
            wrong_char = random.choice(wrong_chars)
            element.send_keys(wrong_char)
            time.sleep(HumanBehavior.typing_delay())
            
            # Пауза "осознания" ошибки
            time.sleep(random.uniform(0.5, 1.2))
            
            # Удаляем ошибку
            element.send_keys(Keys.BACK_SPACE)
            time.sleep(HumanBehavior.typing_delay())
        
        # Печатаем правильный текст
        for i, char in enumerate(text):
            element.send_keys(char)
            
            # Базовая задержка между символами
            delay = HumanBehavior.typing_delay()
            
            # Увеличенная пауза между словами
            if char == ' ':
                delay += HumanBehavior.word_pause()
                logger.debug("⌛ Word pause")
            
            # Случайные более длинные паузы (имитация раздумий)
            if random.random() < 0.1:  # 10% шанс
                delay += random.uniform(0.5, 1.5)
                logger.debug("🤔 Thinking pause")
            
            time.sleep(delay)
            
            # Случайная ошибка в середине (редко)
            if i > 0 and i < len(text) - 1 and random.random() < 0.03:  # 3% шанс
                logger.debug("🔄 Mid-typing correction")
                
                # Неправильный символ
                wrong_char = random.choice('qwertyuiop')
                element.send_keys(wrong_char)
                time.sleep(HumanBehavior.typing_delay())
                
                # Удаляем
                element.send_keys(Keys.BACK_SPACE)
                time.sleep(HumanBehavior.typing_delay())
        
        logger.debug(f"✅ Finished typing '{text}'")
    
    @staticmethod
    def human_scroll(driver, direction: str = 'down', pixels: int = None) -> None:
        """
        Человекоподобная прокрутка страницы
        
        Args:
            driver: WebDriver
            direction: Направление ('down' или 'up')  
            pixels: Количество пикселей (случайное если не указано)
        """
        if pixels is None:
            pixels = random.randint(200, 600)
        
        logger.debug(f"📜 Human scroll {direction}: {pixels}px")
        
        if direction == 'down':
            driver.execute_script(f"window.scrollBy(0, {pixels});")
        else:
            driver.execute_script(f"window.scrollBy(0, -{pixels});")
        
        # Пауза после прокрутки
        time.sleep(random.uniform(0.5, 1.5))
    
    @staticmethod
    def micro_movements(driver, element: WebElement, count: int = None) -> None:
        """
        Микро-движения мыши перед кликом (имитация неточности человека)
        
        Args:
            driver: WebDriver
            element: Элемент для наведения
            count: Количество движений (случайное если не указано)
        """
        if count is None:
            count = random.randint(1, 3)
        
        logger.debug(f"🐭 Micro movements: {count}")
        
        actions = ActionChains(driver)
        
        # Серия небольших движений к элементу
        for i in range(count):
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            
            try:
                actions.move_to_element_with_offset(element, offset_x, offset_y)
                actions.pause(random.uniform(0.1, 0.3))
            except Exception as e:
                logger.debug(f"Micro movement failed: {e}")
                break
        
        try:
            actions.perform()
        except Exception as e:
            logger.debug(f"Micro movements failed: {e}")
    
    @staticmethod
    def simulate_reading_element(driver, element: WebElement) -> None:
        """
        Имитация чтения элемента (прокрутка к нему + пауза)
        
        Args:
            driver: WebDriver
            element: Элемент для 'чтения'
        """
        try:
            # Прокручиваем к элементу
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            
            # Пауза для 'чтения'
            reading_time = HumanBehavior.reading_pause()
            logger.debug(f"📖 Reading element for {reading_time:.1f}s")
            time.sleep(reading_time)
            
        except Exception as e:
            logger.debug(f"Reading simulation failed: {e}")
            # Fallback пауза
            time.sleep(random.uniform(1, 3))
    
    @staticmethod
    def random_mouse_movement(driver) -> None:
        """
        Случайное движение мыши по странице (имитация изучения)
        
        Args:
            driver: WebDriver
        """
        try:
            # Получаем размер окна
            window_size = driver.get_window_size()
            width = window_size['width']
            height = window_size['height']
            
            # Случайная точка для движения
            x = random.randint(100, width - 100)
            y = random.randint(100, height - 200)
            
            logger.debug(f"🎯 Random mouse movement to ({x}, {y})")
            
            actions = ActionChains(driver)
            actions.move_by_offset(x, y)
            actions.pause(random.uniform(0.5, 1.0))
            actions.perform()
            
        except Exception as e:
            logger.debug(f"Random mouse movement failed: {e}")
    
    @staticmethod
    def human_click_with_preparation(driver, element: WebElement, preparation: bool = True) -> None:
        """
        Человекоподобный клик с подготовкой
        
        Args:
            driver: WebDriver
            element: Элемент для клика
            preparation: Выполнять ли подготовительные действия
        """
        if preparation:
            # Прокрутка к элементу
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(random.uniform(0.5, 1.5))
            
            # Микро-движения мыши
            HumanBehavior.micro_movements(driver, element)
            
            # Небольшая пауза перед кликом
            time.sleep(random.uniform(0.2, 0.8))
        
        # Сам клик
        try:
            element.click()
            logger.debug("✅ Human click executed")
        except Exception as e:
            logger.debug(f"Click failed, trying JS click: {e}")
            driver.execute_script("arguments[0].click();", element)
    
    @staticmethod
    def wait_with_human_behavior(driver, seconds: float) -> None:
        """
        Ожидание с имитацией человеческого поведения
        
        Args:
            driver: WebDriver
            seconds: Время ожидания в секундах
        """
        logger.debug(f"⏳ Human wait: {seconds:.1f}s with behavior")
        
        # Разбиваем время на части
        chunks = max(1, int(seconds / 3))  # 3-секундные части
        chunk_time = seconds / chunks
        
        for i in range(chunks):
            time.sleep(chunk_time)
            
            # Случайное поведение во время ожидания
            if random.random() < 0.3:  # 30% шанс
                behavior = random.choice(['scroll', 'mouse_move', 'nothing'])
                
                if behavior == 'scroll':
                    HumanBehavior.human_scroll(driver, random.choice(['up', 'down']), random.randint(50, 200))
                elif behavior == 'mouse_move':
                    HumanBehavior.random_mouse_movement(driver)
                # 'nothing' - просто ждем