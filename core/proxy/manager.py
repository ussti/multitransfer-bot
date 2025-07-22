"""
Proxy Manager with Proxy6.net API Integration
Менеджер прокси с интеграцией API Proxy6.net
"""

import logging
import asyncio
import aiohttp
import random
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ProxyManager:
    """Менеджер прокси с интеграцией Proxy6.net API"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = False
        self.proxies = []
        self.failed_proxies = set()
        self.last_fetch_time = None
        self.api_key = None
        self.base_url = "https://px6.link/api"
        
        # Проверяем временное отключение прокси
        proxy_disabled_file = "/tmp/proxy_disabled"
        if os.path.exists(proxy_disabled_file):
            self.enabled = False
            logger.info("🌐 ProxyManager initialized in DISABLED mode (temporarily disabled)")
        # Проверяем наличие конфигурации прокси
        elif config and config.get('proxy', {}).get('api_key'):
            self.enabled = True
            self.api_key = config.get('proxy', {}).get('api_key')
            self.country = config.get('proxy', {}).get('country', 'ru')
            logger.info("🌐 ProxyManager initialized with Proxy6.net API")
        else:
            logger.info("🌐 ProxyManager initialized in direct mode (no proxy)")
    
    async def get_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Получить рабочий прокси для использования
        
        Returns:
            None для прямого соединения или словарь с данными прокси
        """
        if not self.enabled:
            logger.debug("🌐 Using direct connection (proxy disabled)")
            return None
        
        if not self.api_key:
            logger.warning("⚠️ Proxy API key not configured, using direct connection")
            return None
        
        # Обновляем список прокси при необходимости
        if not self.proxies or self._need_refresh():
            await self._fetch_proxies()
        
        # Ищем рабочий прокси
        working_proxies = [p for p in self.proxies if f"{p['ip']}:{p['port']}" not in self.failed_proxies]
        
        if not working_proxies:
            logger.warning("⚠️ No working proxies available, using direct connection")
            return None
        
        # Возвращаем случайный рабочий прокси
        proxy = random.choice(working_proxies)
        logger.info(f"🌐 Using proxy: {proxy['ip']}:{proxy['port']} ({proxy['country']})")
        return proxy
    
    async def mark_proxy_failed(self, ip: str, port: str, error: str = None):
        """
        Отметить прокси как проблемный
        
        Args:
            ip: IP адрес прокси
            port: Порт прокси
            error: Описание ошибки (опционально)
        """
        if not self.enabled:
            return
        
        proxy_key = f"{ip}:{port}"
        self.failed_proxies.add(proxy_key)
        
        logger.warning(f"⚠️ Proxy {proxy_key} marked as failed: {error or 'Unknown error'}")
        logger.info(f"📊 Failed proxies count: {len(self.failed_proxies)}/{len(self.proxies)}")
        
        # TODO: Добавить в базу данных для постоянного хранения статистики
    
    async def mark_proxy_success(self, ip: str, port: str, response_time: float = 0):
        """
        Отметить успешное использование прокси
        
        Args:
            ip: IP адрес прокси
            port: Порт прокси
            response_time: Время ответа в секундах
        """
        if not self.enabled:
            return
        
        proxy_key = f"{ip}:{port}"
        
        # Удаляем из списка проблемных, если он там был
        self.failed_proxies.discard(proxy_key)
        
        logger.info(f"✅ Proxy {proxy_key} used successfully (response time: {response_time:.2f}s)")
        logger.debug(f"📊 Working proxies: {len(self.proxies) - len(self.failed_proxies)}/{len(self.proxies)}")
        
        # TODO: Добавить в базу данных для постоянного хранения статистики
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику прокси
        
        Returns:
            Словарь со статистикой
        """
        working_count = len(self.proxies) - len(self.failed_proxies) if self.proxies else 0
        return {
            'enabled': self.enabled,
            'total_proxies': len(self.proxies),
            'working_proxies': working_count,
            'failed_proxies': len(self.failed_proxies),
            'success_rate': f"{(working_count/len(self.proxies)*100):.1f}%" if self.proxies else "0%",
            'mode': 'direct' if not self.enabled else 'proxy',
            'api_key_configured': bool(self.api_key),
            'last_update': self.last_fetch_time.isoformat() if self.last_fetch_time else None
        }
    
    def is_enabled(self) -> bool:
        """Проверить, включены ли прокси"""
        return self.enabled
    
    async def initialize(self) -> bool:
        """
        Инициализация прокси-менеджера
        
        Returns:
            True если инициализация прошла успешно
        """
        if not self.enabled:
            logger.info("✅ ProxyManager initialized in direct mode")
            return True
        
        try:
            await self._fetch_proxies()
            logger.info("✅ ProxyManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ ProxyManager initialization failed: {e}")
            self.enabled = False  # Переключаемся в режим прямого соединения
            return True  # Все равно возвращаем True, так как можем работать без прокси
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.enabled:
            logger.info("🔒 ProxyManager shutdown")
    
    def _need_refresh(self) -> bool:
        """Проверить, нужно ли обновить список прокси"""
        if not self.last_fetch_time:
            return True
        
        # Обновляем каждые 5 минут
        return datetime.utcnow() - self.last_fetch_time > timedelta(minutes=5)
    
    async def _fetch_proxies(self):
        """Получить список прокси через API Proxy6.net"""
        try:
            logger.info("🔄 Fetching proxies from Proxy6.net API...")
            
            async with aiohttp.ClientSession() as session:
                # Получаем список прокси
                url = f"{self.base_url}/{self.api_key}/getproxy"
                params = {
                    'state': 'active'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == 'yes':
                            self.proxies = []
                            
                            # ИСПРАВЛЕНО: Парсим данные согласно документации
                            proxy_list = data.get('list', {})
                            
                            # API возвращает словарь вида {"11": {...}, "22": {...}}
                            if isinstance(proxy_list, dict):
                                for proxy_id, proxy_info in proxy_list.items():
                                    proxy_data = {
                                        'id': proxy_info.get('id', proxy_id),
                                        'ip': proxy_info.get('ip', proxy_info.get('host', '')),
                                        'port': str(proxy_info.get('port', '')),
                                        'user': proxy_info.get('user', ''),
                                        'pass': proxy_info.get('pass', ''),
                                        'country': proxy_info.get('country', 'ru'),
                                        'type': proxy_info.get('type', 'http'),
                                        'date_end': proxy_info.get('date_end', ''),
                                        'active': proxy_info.get('active', '0') == '1'  # Строка!
                                    }
                                    
                                    # Добавляем только активные прокси с валидными данными
                                    if proxy_data['active'] and proxy_data['ip'] and proxy_data['port']:
                                        self.proxies.append(proxy_data)
                            
                            # Fallback для списка (если вдруг API изменится)
                            elif isinstance(proxy_list, list):
                                for proxy_info in proxy_list:
                                    proxy_data = {
                                        'id': proxy_info.get('id', ''),
                                        'ip': proxy_info.get('ip', proxy_info.get('host', '')),
                                        'port': str(proxy_info.get('port', '')),
                                        'user': proxy_info.get('user', ''),
                                        'pass': proxy_info.get('pass', ''),
                                        'country': proxy_info.get('country', 'ru'),
                                        'type': proxy_info.get('type', 'http'),
                                        'date_end': proxy_info.get('date_end', ''),
                                        'active': proxy_info.get('active', 0) == 1
                                    }
                                    
                                    if proxy_data['active'] and proxy_data['ip'] and proxy_data['port']:
                                        self.proxies.append(proxy_data)
                            
                            self.last_fetch_time = datetime.utcnow()
                            logger.info(f"✅ Fetched {len(self.proxies)} active proxies")
                            
                        else:
                            logger.error(f"❌ Proxy API error: {data.get('error_id', 'Unknown error')}")
                            
                    else:
                        logger.error(f"❌ HTTP error {response.status} when fetching proxies")
                        
        except Exception as e:
            logger.error(f"❌ Error fetching proxies: {e}")
    
    async def _check_proxy_health(self, proxy: Dict[str, Any]) -> bool:
        """Проверить работоспособность прокси"""
        try:
            proxy_url = f"http://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://httpbin.org/ip',
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return True
                    
        except Exception as e:
            logger.debug(f"Proxy health check failed for {proxy['ip']}:{proxy['port']}: {e}")
            
        return False


# Для обратной совместимости создаем простую функцию
async def create_proxy_manager(config: Optional[Dict[str, Any]] = None) -> ProxyManager:
    """
    Создать и инициализировать ProxyManager
    
    Args:
        config: Конфигурация (опционально)
        
    Returns:
        Инициализированный ProxyManager
    """
    manager = ProxyManager(config)
    await manager.initialize()
    return manager