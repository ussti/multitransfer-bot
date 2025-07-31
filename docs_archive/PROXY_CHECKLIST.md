# ✅ ЧЕКЛИСТ НАСТРОЙКИ ПРОКСИ

## 🚀 БЫСТРАЯ ИНТЕГРАЦИЯ (30 минут)

### Шаг 1: Проверка готовности системы (5 мин)
- [ ] VPN отключен
- [ ] `rm -f /tmp/proxy_disabled` выполнено
- [ ] Прокси работают: `curl --proxy http://GALsB4:6UwJ3b@196.16.220.52:8000 http://httpbin.org/ip`
- [ ] Автоматизация работает: `PYTHONPATH=. python3 tests/automation/test_complete_automation.py`

### Шаг 2: Модификация main.py (10 мин)
- [ ] Импорт добавлен: `from core.proxy.manager import ProxyManager`
- [ ] ProxyManager создан: `proxy_manager = ProxyManager(config.data)`
- [ ] Передан в PaymentService: `PaymentService(config, proxy_manager=proxy_manager)`

### Шаг 3: Модификация PaymentService (10 мин)
- [ ] `__init__` принимает `proxy_manager=None`
- [ ] `self.proxy_manager = proxy_manager` сохранен
- [ ] MultiTransferAutomation получает прокси: `await self.proxy_manager.get_proxy()`

### Шаг 4: Тестирование (5 мин)
- [ ] Бот запускается: `python main.py`
- [ ] Telegram команда работает: `/payment 1000`
- [ ] Логи показывают прокси: `✅ Proxy auth extension created`

---

## 🔍 ДИАГНОСТИКА ПРОБЛЕМ

### Если НЕ РАБОТАЕТ автоматизация:
- [ ] Проверить селекторы "Все карты"
- [ ] Проверить что браузер запускается
- [ ] Посмотреть логи ошибок

### Если НЕ РАБОТАЕТ прокси:  
- [ ] Проверить curl без VPN
- [ ] Проверить config.yml: `enabled: true`
- [ ] Проверить providers.py: актуальные credentials

### Если ПОЯВЛЯЮТСЯ диалоги Chrome:
- [ ] Проверить что Extension создается
- [ ] Убедиться что SSH tunnel отключен
- [ ] Перезапустить браузер

---

## 📋 КОНФИГУРАЦИЯ ФАЙЛОВ

### config.yml
```yaml
proxy:
  enabled: true
  use_ssh_tunnel: false
```

### core/proxy/providers.py  
```python
# Убедиться что credentials актуальны:
'user': 'GALsB4', 'pass': '6UwJ3b'  # Немецкий
'user': '2G4L9A', 'pass': 'pphKeV'  # Российский 1
'user': 'gzqPrg', 'pass': 'SJHhke'  # Российский 2
```

### main.py (добавить)
```python
from core.proxy.manager import ProxyManager

async def main():
    config = Config()
    proxy_manager = ProxyManager(config.data)
    payment_service = PaymentService(config, proxy_manager=proxy_manager)
```

### core/services/payment_service.py (модифицировать)
```python
def __init__(self, config, proxy_manager=None):
    self.proxy_manager = proxy_manager

async def create_payment(self, ...):
    proxy = await self.proxy_manager.get_proxy() if self.proxy_manager else None
    automation = MultiTransferAutomation(proxy=proxy, ...)
```

---

## 🎯 КРИТЕРИИ УСПЕХА

### ✅ Прокси работает:
- Никаких Chrome диалогов
- Navigation successful через прокси
- IP изменился (немецкий/российский)
- "Все карты" находится и выбирается

### ✅ Интеграция работает:
- `/payment 1000` запускается
- Все 6 шагов выполняются
- QR код/ссылка возвращается
- Ошибки обрабатываются gracefully

### ✅ Производительность:
- <10 секунд на навигацию
- <40 секунд на полный цикл
- >95% успешных операций

---

## 🚨 ВАЖНЫЕ КОМАНДЫ

```bash
# Тест прокси (БЕЗ VPN!)
curl --proxy http://GALsB4:6UwJ3b@196.16.220.52:8000 http://httpbin.org/ip

# Включить прокси
rm -f /tmp/proxy_disabled

# Полный тест автоматизации  
PYTHONPATH=. python3 tests/automation/test_complete_automation.py

# Запуск бота
python main.py

# Мониторинг прокси логов
tail -f logs/app.log | grep -i proxy

# Проверка конфигурации
grep -A 5 "proxy:" config.yml
```

---

## 📞 ПОДДЕРЖКА

Если что-то не работает:
1. Проверить все пункты чеклиста ✅
2. Посмотреть логи ошибок 
3. Сравнить с рабочей конфигурацией в `PROXY_SETUP_GUIDE.md`
4. Убедиться что VPN отключен
5. Перезапустить браузер/бот

⚠️ **ВНИМАНИЕ: ЭТОТ ФАЙЛ УСТАРЕЛ!**

**НОВЫЙ ПОДХОД:** Вместо исправления существующей логики, мы интегрируем рабочий BrowserManager.

**ИСПОЛЬЗУЙТЕ АКТУАЛЬНЫЕ ФАЙЛЫ:**
- `PROXY_INTEGRATION_PLAN.md` - актуальный технический план
- `INTEGRATION_CHECKLIST.md` - актуальный чеклист выполнения
- `FILES_TO_MODIFY.md` - точный список изменений
- `TESTING_PLAN.md` - план тестирования

**Chrome Extension - проверенное решение!**
**SSH Tunnel - экспериментальная функция (можно игнорировать ошибки)**