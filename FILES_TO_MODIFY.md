# 📁 ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

## 🎯 ОСНОВНЫЕ ФАЙЛЫ (ОБЯЗАТЕЛЬНЫЕ)

### 1. `core/services/payment_service.py` ⭐⭐⭐⭐⭐
**Изменения:**
- Добавить параметр `browser_manager_factory=None` в `__init__`
- Добавить флаг переключения в `create_payment`
- Переименовать текущий метод в `_create_payment_legacy`
- Создать новый метод `_create_payment_with_browser_manager`
- Адаптировать логику из тестов

### 2. `main.py` ⭐⭐⭐⭐
**Изменения:**
- Добавить импорт `BrowserManager`
- Создать функцию `browser_manager_factory`
- Передать фабрику в `PaymentService` (строка 577)

## 🛠️ ДОПОЛНИТЕЛЬНЫЕ ФАЙЛЫ (ПО НЕОБХОДИМОСТИ)

### 3. `PROXY_INTEGRATION_PLAN.md` ✅ (уже создан)
**Статус:** Готов

### 4. `INTEGRATION_CHECKLIST.md` ✅ (уже создан)  
**Статус:** Готов

### 5. `PROXY_SETUP_GUIDE.md` 
**Возможные изменения:**
- Обновить инструкции для нового режима
- Добавить документацию по флагу `USE_BROWSER_MANAGER`

### 6. `PROXY_CHECKLIST.md`
**Возможные изменения:**
- Добавить проверки для нового режима
- Обновить команды тестирования

## 🚫 ФАЙЛЫ КОТОРЫЕ НЕ ТРОГАЕМ

### ✅ Рабочие файлы (НЕ ИЗМЕНЯЕМ):
- `web/browser/manager.py` - рабочий BrowserManager
- `tests/automation/test_complete_automation.py` - рабочие тесты
- `web/browser/multitransfer.py` - оставляем как есть для legacy режима
- `core/proxy/manager.py` - рабочий ProxyManager
- `core/proxy/providers.py` - рабочие прокси

### 🔒 Критические файлы (НЕ ТРОГАЕМ):
- Все файлы в `tests/` - могут сломать рабочие тесты
- `core/database/` - не связано с прокси
- `bot/` - handlers Telegram бота
- `utils/` - общие утилиты

## 📋 ДЕТАЛЬНЫЙ ПЛАН ИЗМЕНЕНИЙ

### В `core/services/payment_service.py`:

#### Текущий код (строки 32-33):
```python
async def create_payment(
    self, 
    user_id: int, 
    amount: float,
```

#### Изменится на:
```python
def __init__(self, session, proxy_manager=None, browser_manager_factory=None):
    # Добавляем новый параметр
    self.browser_manager_factory = browser_manager_factory

async def create_payment(self, user_id: int, amount: float, ...):
    # Добавляем проверку флага
    use_browser_manager = os.getenv('USE_BROWSER_MANAGER', 'false') == 'true'
    
    if use_browser_manager and self.browser_manager_factory:
        return await self._create_payment_with_browser_manager(...)
    else:
        return await self._create_payment_legacy(...)
```

#### Текущий код (строки 117-118):
```python
automation = MultiTransferAutomation(proxy=proxy, config=self.config.to_dict())
result = await automation.create_payment(automation_data)
```

#### Переносится в:
```python
async def _create_payment_legacy(self, ...):
    # ВСЯ существующая логика без изменений
    automation = MultiTransferAutomation(proxy=proxy, config=self.config.to_dict())
    result = await automation.create_payment(automation_data)
    # ... остальная логика
```

#### Добавляется новый метод:
```python
async def _create_payment_with_browser_manager(self, ...):
    browser_manager = self.browser_manager_factory(self.config, proxy_manager=self.proxy_manager)
    async with browser_manager:
        success = await browser_manager.start_browser(use_proxy=True)
        if success:
            # Адаптированная логика из тестов
            result = await self._run_automation_steps(browser_manager.driver, automation_data)
        # ... обработка результата
```

### В `main.py`:

#### Текущий код (строка 26):
```python
from core.services.payment_service import PaymentService
```

#### Добавится:
```python
from core.services.payment_service import PaymentService
from web.browser.manager import BrowserManager  # НОВЫЙ ИМПОРТ
```

#### Текущий код (строка 577):
```python
payment_service = PaymentService(session, proxy_manager=proxy_manager)
```

#### Изменится на:
```python
# Добавляем фабрику
def browser_manager_factory(config, proxy_manager):
    browser_config = {
        'headless': True,
        'window_size': '1920,1080', 
        'implicit_wait': 10,
        'page_load_timeout': 60
    }
    return BrowserManager(browser_config, proxy_manager=proxy_manager)

payment_service = PaymentService(
    session, 
    proxy_manager=proxy_manager,
    browser_manager_factory=browser_manager_factory  # НОВЫЙ ПАРАМЕТР
)
```

## ⚠️ РИСКИ И МИТИГАЦИЯ

### 🚨 Высокий риск:
1. **Сломать существующую логику** → Mitigation: Сохраняем все в `_create_payment_legacy`
2. **Сломать тесты** → Mitigation: НЕ трогаем тестовые файлы
3. **Конфликт зависимостей** → Mitigation: Используем фабрику вместо прямых импортов

### ⚠️ Средний риск:
1. **Неправильная адаптация логики** → Mitigation: Копируем точно из рабочих тестов
2. **Проблемы с async/await** → Mitigation: Следуем примеру тестов с `async with`

### ⚡ Низкий риск:
1. **Проблемы с конфигурацией** → Mitigation: Используем ту же конфигурацию что в тестах
2. **Различия в окружении** → Mitigation: Флаг позволяет быстро переключиться

## 🎯 ПОРЯДОК ИЗМЕНЕНИЙ

1. **Сначала:** Создать backup файлы
2. **Затем:** Изменить `payment_service.py`
3. **Потом:** Изменить `main.py`
4. **Наконец:** Протестировать оба режима

---

**ПРИНЦИП: МИНИМАЛЬНЫЕ ИЗМЕНЕНИЯ, МАКСИМАЛЬНАЯ БЕЗОПАСНОСТЬ**