# 🌐 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ ПРОКСИ

## 📋 БЫСТРЫЙ ЧЕКЛИСТ ДЛЯ CLAUDE

### ✅ Проверка текущей конфигурации
- [ ] Проверить `config.yml` - прокси включены
- [ ] Убедиться что `use_ssh_tunnel: false` (используем Chrome Extension)
- [ ] Проверить наличие рабочих прокси в `core/proxy/providers.py`

### ✅ Тестирование прокси
```bash
# 1. Протестировать прокси напрямую (без VPN!)
curl --connect-timeout 10 --proxy http://GALsB4:6UwJ3b@196.16.220.52:8000 http://httpbin.org/ip

# 2. Убедиться что /tmp/proxy_disabled НЕ существует
rm -f /tmp/proxy_disabled

# 3. Запустить тест автоматизации
PYTHONPATH=/Users/ussti/Desktop/multitransfer-bot python3 tests/automation/test_complete_automation.py
```

### ✅ Ожидаемые логи при успехе
```
✅ Proxy auth extension created
✅ Browser started successfully in proxy mode
✅ Navigation successful
✅ Proxy XXX.XXX.XXX.XXX:8000 used successfully
```

### ✅ Признаки проблем
```
❌ Browser connection test failed
❌ SSH tunnel creation failed (это OK, fallback работает)
⚠️ Browser connection test failed - no expected content
```

---

## 🔧 ПОЛНАЯ ИНСТРУКЦИЯ

### 1. Архитектура прокси

#### Текущая рабочая схема:
```
User Request → ProxyManager → Chrome Extension → Upstream Proxy → Website
```

#### Компоненты:
- **ProxyManager** (`core/proxy/manager.py`) - управление прокси
- **Proxy6Provider** (`core/proxy/providers.py`) - статические прокси
- **Chrome Extension** - автоматическая авторизация (без диалогов)
- **SSH Tunnel** - альтернатива (временно отключена)

### 2. Конфигурация прокси

#### Файл: `config.yml`
```yaml
proxy:
  enabled: true
  use_ssh_tunnel: false  # Используем Chrome Extension
  tunnel_timeout: 30
```

#### Файл: `core/proxy/providers.py`
Актуальные прокси (приоритет: Германия → Россия):
```python
# Немецкий SOCKS5 (приоритет)
{
    'id': 'proxy6_de_socks5',
    'ip': '196.16.220.52',
    'port': '8000', 
    'user': 'GALsB4',
    'pass': '6UwJ3b',
    'country': 'de',
    'type': 'socks5'
}

# Российские HTTP (fallback)
{
    'ip': '45.10.65.50',
    'port': '8000',
    'user': '2G4L9A', 
    'pass': 'pphKeV',
    'type': 'http'
}
```

### 3. Интеграция в основной бот

#### 3.1 Модификация `main.py`
```python
from core.proxy.manager import ProxyManager

# В функции main()
config = Config()
proxy_manager = ProxyManager(config.data)

# Передать в PaymentService
payment_service = PaymentService(config, proxy_manager=proxy_manager)
```

#### 3.2 Модификация `core/services/payment_service.py`
```python
def __init__(self, config, proxy_manager=None):
    self.proxy_manager = proxy_manager
    
async def create_payment(self, ...):
    # Использовать proxy_manager в MultiTransferAutomation
    automation = MultiTransferAutomation(
        proxy=await self.proxy_manager.get_proxy() if self.proxy_manager else None,
        config=self.config,
        proxy_manager=self.proxy_manager
    )
```

### 4. Тестирование интеграции

#### 4.1 Запуск бота с прокси
```bash
python main.py
```

#### 4.2 Тестирование через Telegram
```
/start
/settings  # настроить реквизиты получателя
/payment 1000  # запустить платеж
```

#### 4.3 Мониторинг логов
```bash
tail -f logs/app.log | grep -E "(proxy|Proxy|PROXY)"
```

### 5. Диагностика проблем

#### Проблема: Chrome диалоги авторизации
**Решение:** Убедиться что Chrome Extension создается:
```
✅ Proxy auth extension created: /path/to/extension
```

#### Проблема: Прокси не работает
**Диагностика:**
```bash
# Тест без VPN
curl --proxy http://user:pass@ip:port http://httpbin.org/ip

# Проверить конфигурацию
grep -A 10 "proxy:" config.yml
```

#### Проблема: SSH туннель ошибки
**Решение:** Это нормально, используется fallback на Chrome Extension:
```
WARNING: SSH tunnel failed: ... falling back to direct proxy
✅ Proxy auth extension created
```

### 6. Мониторинг производительности

#### Целевые метрики:
- **Время навигации:** <10 секунд через прокси
- **Полный цикл:** <40 секунд (все 14 шагов)
- **Успешность:** >95% операций

#### Команды мониторинга:
```bash
# Статистика прокси
grep "used successfully" logs/app.log | tail -10

# Ошибки прокси  
grep "proxy.*failed" logs/app.log | tail -10

# Производительность
grep "response time" logs/app.log | tail -10
```

---

## 🚨 ВАЖНЫЕ ЗАМЕЧАНИЯ

### ⚠️ Требования окружения:
1. **VPN должен быть ОТКЛЮЧЕН** при тестировании прокси
2. **macOS может показывать системные диалоги** - это обходится Chrome Extension
3. **Прокси могут истекать** - нужно обновлять credentials

### ✅ Признаки успешной работы:
1. Никаких диалогов авторизации Chrome
2. Сайт загружается через зарубежный IP
3. "Все карты" находится и выбирается
4. Все 14 шагов выполняются

### 🔄 План развертывания:
1. Интегрировать в main.py (30 мин)
2. Протестировать через Telegram (1 час)  
3. Проверить все 14 шагов (2-3 часа)
4. Оптимизировать производительность (1 день)
5. Развернуть в продакшене (1 день)

---

*Последнее обновление: 31 июля 2025*
*Статус: УСТАРЕЛ - см. PROXY_INTEGRATION_PLAN.md*
*Новый подход: Интеграция BrowserManager вместо исправления MultiTransferAutomation*

⚠️ **ВНИМАНИЕ: ЭТОТ ФАЙЛ УСТАРЕЛ!**
Используйте вместо него:
- `PROXY_INTEGRATION_PLAN.md` - актуальный план
- `INTEGRATION_CHECKLIST.md` - актуальный чеклист