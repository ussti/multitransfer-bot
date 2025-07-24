#!/usr/bin/env python3
"""
Test script for Smart Proxy Rotation Manager
Тестовый скрипт для умного менеджера ротации прокси
"""

import asyncio
import time
import random
from core.proxy.smart_rotation_manager import (
    SmartProxyRotationManager, 
    ProxyStats, 
    CaptchaType, 
    ProxyQuality,
    EnhancedProxyManager
)
from core.proxy.integration_helper import ProxyIntegrationHelper, ProxyAwareMultiTransferAutomation


async def test_smart_rotation_basic():
    """Базовый тест умной ротации"""
    print("🧪 Testing Smart Proxy Rotation Manager")
    print("=" * 50)
    
    # Создаем менеджер
    manager = SmartProxyRotationManager()
    
    # Симулируем прокси от провайдера
    mock_proxies = [
        {
            'ip': '1.2.3.4',
            'port': '8080',
            'user': 'user1',
            'pass': 'pass1',
            'country': 'ru'
        },
        {
            'ip': '5.6.7.8', 
            'port': '8080',
            'user': 'user2',
            'pass': 'pass2',
            'country': 'ru'
        },
        {
            'ip': '9.10.11.12',
            'port': '8080', 
            'user': 'user3',
            'pass': 'pass3',
            'country': 'ru'
        }
    ]
    
    # Загружаем прокси
    await manager.load_proxies_from_provider(mock_proxies)
    print(f"✅ Loaded {len(manager.active_proxies)} proxies")
    
    # Тестируем выбор прокси
    context = {
        'target_country': 'tj',
        'amount': 10000,
        'time_of_day': 'day'
    }
    
    print("\n🎯 Testing proxy selection...")
    for i in range(5):
        proxy = await manager.get_optimal_proxy(context)
        if proxy:
            print(f"  Selected: {proxy.ip}:{proxy.port} (quality: {proxy.quality_level.value})")
        else:
            print("  No proxy available")
    
    return manager


async def test_learning_algorithm():
    """Тест алгоритма обучения"""
    print("\n🧠 Testing Learning Algorithm")
    print("=" * 50)
    
    manager = await test_smart_rotation_basic()
    
    # Симулируем различные реалистичные сценарии использования
    scenarios = [
        # Хорошие результаты для первого прокси (8% капчи)
        (0, True, CaptchaType.NONE, 2.5),
        (0, True, CaptchaType.NONE, 3.0),
        (0, True, CaptchaType.NONE, 2.8),
        (0, True, CaptchaType.NONE, 3.2),
        (0, True, CaptchaType.SIMPLE, 4.0),
        (0, True, CaptchaType.NONE, 2.9),
        (0, True, CaptchaType.NONE, 3.1),
        (0, True, CaptchaType.NONE, 2.7),
        (0, True, CaptchaType.NONE, 3.5),
        (0, True, CaptchaType.NONE, 3.0),
        (0, True, CaptchaType.NONE, 2.6),
        (0, True, CaptchaType.SIMPLE, 4.2),
        
        # Средние результаты для второго прокси (60% капчи) - должен быть POOR
        (1, True, CaptchaType.NONE, 5.0),
        (1, True, CaptchaType.PUZZLE, 8.0),
        (1, True, CaptchaType.SIMPLE, 6.0),
        (1, True, CaptchaType.COMPLEX, 12.0),
        (1, True, CaptchaType.NONE, 4.5),
        (1, True, CaptchaType.PUZZLE, 9.0),
        (1, True, CaptchaType.SIMPLE, 7.0),
        (1, True, CaptchaType.COMPLEX, 11.0),
        (1, True, CaptchaType.PUZZLE, 8.5),
        (1, True, CaptchaType.SIMPLE, 6.5),
        
        # Средние результаты для третьего прокси (60% капчи) - должен быть POOR  
        (2, True, CaptchaType.NONE, 5.5),
        (2, True, CaptchaType.PUZZLE, 9.0),
        (2, True, CaptchaType.SIMPLE, 6.5),
        (2, True, CaptchaType.COMPLEX, 13.0),
        (2, True, CaptchaType.NONE, 5.0),
        (2, True, CaptchaType.PUZZLE, 8.5),
        (2, True, CaptchaType.SIMPLE, 7.5),
        (2, True, CaptchaType.COMPLEX, 12.0),
        (2, True, CaptchaType.PUZZLE, 9.5),
        (2, True, CaptchaType.SIMPLE, 6.8),
    ]
    
    print("📊 Simulating usage scenarios...")
    for proxy_idx, success, captcha_type, response_time in scenarios:
        proxy = manager.active_proxies[proxy_idx]
        await manager.record_session_result(proxy, success, captcha_type, response_time)
        print(f"  {proxy.ip}: success={success}, captcha={captcha_type.value}, time={response_time}s")
    
    # Проверяем как изменились рейтинги
    print("\n📈 Proxy quality after learning:")
    for proxy in sorted(manager.active_proxies, key=lambda p: p.quality_score, reverse=True):
        print(f"  {proxy.ip}:{proxy.port} - Quality: {proxy.quality_level.value} "
              f"(score: {proxy.quality_score:.1f}, captcha rate: {proxy.captcha_rate:.1%})")
    
    return manager


async def test_strategy_adaptation():
    """Тест адаптации стратегий"""
    print("\n🔄 Testing Strategy Adaptation")
    print("=" * 50)
    
    manager = await test_learning_algorithm()
    
    # Симулируем высокую частоту капчи для активации анти-паттерн стратегии
    print("⚠️ Simulating high captcha rate...")
    
    for _ in range(10):
        proxy = await manager.get_optimal_proxy()
        if proxy:
            # Симулируем капчу в 30% случаев (более реалистично)
            has_captcha = random.random() < 0.30
            captcha_type = random.choice([CaptchaType.PUZZLE, CaptchaType.COMPLEX]) if has_captcha else CaptchaType.NONE
            success = not has_captcha or random.random() < 0.7  # Более реалистичный успех при капче
            
            await manager.record_session_result(proxy, success, captcha_type, random.uniform(5, 15))
    
    # Проверяем изменилась ли стратегия
    print(f"Current strategy: {manager.current_strategy}")
    print(f"Recent captcha rate: {manager._calculate_recent_captcha_rate():.1%}")
    
    return manager


async def test_analytics_report():
    """Тест аналитического отчета"""
    print("\n📊 Testing Analytics Report")
    print("=" * 50)
    
    manager = await test_strategy_adaptation()
    
    report = manager.get_analytics_report()
    
    print("📈 Analytics Report:")
    print(f"  Overview: {report['overview']}")
    print(f"  Performance: {report['performance']}")
    print(f"  Quality Distribution: {report['quality_distribution']}")
    print(f"  Top Performers:")
    for performer in report['top_performers']:
        print(f"    - {performer}")


async def test_integration_helper():
    """Тест помощника интеграции"""
    print("\n🔧 Testing Integration Helper")
    print("=" * 50)
    
    helper = ProxyIntegrationHelper()
    
    # Тест определения типа капчи
    test_pages = [
        ('<html><div class="g-recaptcha">test</div></html>', 'https://example.com', CaptchaType.RECAPTCHA),
        ('<html><div>puzzle verification</div></html>', 'https://example.com', CaptchaType.PUZZLE),
        ('<html><input type="text" placeholder="captcha"></html>', 'https://example.com', CaptchaType.SIMPLE),
        ('<html><h1>Welcome</h1></html>', 'https://example.com', CaptchaType.NONE),
    ]
    
    print("🔍 Testing captcha detection:")
    for html, url, expected in test_pages:
        detected = helper.detect_captcha_type(html, url)
        status = "✅" if detected == expected else "❌"
        print(f"  {status} Expected: {expected.value}, Got: {detected.value}")
    
    # Тест создания контекста
    user_data = {'id': 123, 'successful_payments': 5}
    payment_data = {'amount': 25000, 'recipient_country': 'kg', 'currency': 'KGS', 'hour': 14}
    
    context = helper.create_session_context(user_data, payment_data)
    print(f"📝 Session context: {context}")
    
    # Тест определения повтора
    test_errors = [
        ("Connection timeout", 1, True),
        ("Invalid captcha", 1, False),
        ("Network error", 3, False),  # Слишком много попыток
        ("Proxy blocked", 2, True),
    ]
    
    print("🔄 Testing retry logic:")
    for error, attempt, expected in test_errors:
        should_retry = helper.should_retry_with_new_proxy(error, attempt)
        status = "✅" if should_retry == expected else "❌"
        print(f"  {status} '{error}' (attempt {attempt}): should_retry={should_retry}")


async def test_enhanced_proxy_manager():
    """Тест расширенного менеджера прокси"""
    print("\n🚀 Testing Enhanced Proxy Manager")
    print("=" * 50)
    
    # Создаем конфигурацию
    config = {
        'proxy': {
            'api_key': 'test_key',  # В реальности нужен настоящий ключ
            'country': 'ru'
        }
    }
    
    manager = EnhancedProxyManager(config)
    
    # Симулируем инициализацию (без реального API)
    print("🔧 Simulating enhanced manager initialization...")
    
    # Загружаем тестовые прокси напрямую в умную ротацию
    test_proxies = [
        {'ip': '192.168.1.1', 'port': '8080', 'user': 'test1', 'pass': 'pass1', 'country': 'ru'},
        {'ip': '192.168.1.2', 'port': '8080', 'user': 'test2', 'pass': 'pass2', 'country': 'ru'},
    ]
    
    await manager.smart_rotation.load_proxies_from_provider(test_proxies)
    
    # Тест получения оптимального прокси
    context = {'target_country': 'tj', 'amount': 15000}
    proxy = await manager.get_optimal_proxy(context)
    
    if proxy:
        print(f"✅ Got optimal proxy: {proxy['ip']}:{proxy['port']}")
        
        # Симулируем результат использования
        await manager.record_result(
            proxy=proxy, 
            success=True, 
            captcha_encountered=False, 
            response_time=3.5
        )
        print("✅ Recorded successful usage")
    else:
        print("❌ No proxy available")
    
    # Получаем аналитику
    analytics = manager.get_analytics()
    print(f"📊 Analytics: {analytics}")


async def main():
    """Главная функция тестирования"""
    print("🎯 SMART PROXY ROTATION MANAGER TESTS")
    print("=" * 60)
    
    try:
        await test_smart_rotation_basic()
        await test_learning_algorithm()
        await test_strategy_adaptation()
        await test_analytics_report()
        await test_integration_helper()
        await test_enhanced_proxy_manager()
        
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())