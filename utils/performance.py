"""
Performance Optimizations для MultiTransfer Bot
Оптимизации для ускорения работы бота
"""

import asyncio
from selenium.webdriver.common.by import By
from typing import Dict, Any, List

# 1. Конфигурация для config.yml (в виде комментария)
"""
Применить в config.yml:
browser:
  headless: true  # Ускоряет на 30%
  window_size: "1366,768"  # Меньше размер = быстрее
  page_load_timeout: 15  # Уменьшить с 30
  implicit_wait: 5  # Уменьшить с 10
"""

# 2. Оптимизированные задержки для multitransfer.py
OPTIMIZED_DELAYS = {
    'short': 0.5,    # Вместо 1-2 секунд
    'medium': 1.0,   # Вместо 2-3 секунд  
    'long': 2.0      # Вместо 3-5 секунд
}

# 3. Быстрые селекторы (использовать первыми)
FAST_SELECTORS = {
    'transfer_abroad_btn': "//button[contains(text(), 'ПЕРЕВЕСТИ ЗА РУБЕЖ')]",
    'continue_btn': "//button[contains(text(), 'ПРОДОЛЖИТЬ')]",
    'captcha_generic': "//div[contains(@class, 'captcha')]"
}

# 4. Функция для заполнения поля (заглушка)
async def fill_field_async(driver, field: str, value: str) -> bool:
    """Асинхронное заполнение поля формы"""
    try:
        # Здесь будет логика заполнения поля
        await asyncio.sleep(0.1)  # Имитация задержки
        return True
    except Exception:
        return False

# 5. Параллельное выполнение
async def parallel_fill_form(driver, form_data: Dict[str, str]) -> List[Any]:
    """Заполняет несколько полей параллельно"""
    tasks = []
    for field, value in form_data.items():
        task = asyncio.create_task(fill_field_async(driver, field, value))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# 6. Кэширование селекторов
class SelectorCache:
    """Кэш для селекторов элементов"""
    
    def __init__(self):
        self.cache = {}
    
    def get_element(self, driver, selector: str):
        """Получить элемент из кэша или найти новый"""
        if selector not in self.cache:
            try:
                self.cache[selector] = driver.find_element(By.XPATH, selector)
            except Exception:
                return None
        return self.cache[selector]
    
    def clear_cache(self):
        """Очистить кэш"""
        self.cache.clear()

# 7. Оптимизированная проверка капчи
async def fast_captcha_check(driver) -> bool:
    """Быстрая проверка наличия капчи"""
    try:
        # Проверяем только основные индикаторы
        quick_selectors = [
            "//div[contains(@class, 'captcha')]",
            "//iframe[contains(@src, 'captcha')]"
        ]
        
        for selector in quick_selectors:
            if driver.find_elements(By.XPATH, selector):
                return True
        return False
    except Exception:
        return False

# 8. Целевое время выполнения
TARGET_TIMES = {
    'total_process': 25,      # секунд (было 40)
    'captcha_solve': 8,       # секунд (было 15)
    'form_fill': 12,          # секунд (было 20)
    'navigation': 3           # секунд (было 5)
}

# 9. Функция для мониторинга производительности
class PerformanceMonitor:
    """Мониторинг производительности операций"""
    
    def __init__(self):
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """Начать отсчет времени для операции"""
        import time
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """Завершить отсчет времени и вернуть длительность"""
        import time
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            del self.start_times[operation]
            return duration
        return 0.0
    
    def check_target_time(self, operation: str, duration: float) -> bool:
        """Проверить, уложились ли в целевое время"""
        target = TARGET_TIMES.get(operation)
        if target:
            return duration <= target
        return True

# 10. Функции для оптимизации селекторов
def get_optimized_selector(selector_type: str) -> str:
    """Получить оптимизированный селектор"""
    return FAST_SELECTORS.get(selector_type, "")

def get_optimized_delay(delay_type: str) -> float:
    """Получить оптимизированную задержку"""
    return OPTIMIZED_DELAYS.get(delay_type, 1.0)