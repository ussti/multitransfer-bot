"""
Multi-Provider Proxy Manager with ProxyLine (primary) + Proxy6 (fallback)
Менеджер прокси с поддержкой ProxyLine (основной) + Proxy6 (резервный)
"""

import logging
import asyncio
import aiohttp
import random
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from .validator import proxy_validator
from .ssh_tunnel import SSHTunnelManager, ProxyCredentials

# Proxy data structures (moved from providers.py)
class ProxyVersion(Enum):
    """Proxy version types"""
    IPV4 = "4"
    IPV4_SHARED = "3" 
    IPV6 = "6"

class ProxyType(Enum):
    """Proxy protocol types"""
    HTTP = "http"
    SOCKS5 = "socks"

@dataclass
class ProxyInfo:
    """Proxy information structure"""
    id: str
    ip: str
    host: str
    port: str
    user: str
    password: str
    type: str
    country: str
    date: str
    date_end: str
    active: bool
    
    @property
    def proxy_url(self) -> str:
        """Get proxy URL in format protocol://user:pass@host:port"""
        protocol = "socks5" if self.type == "socks" else "http"
        return f"{protocol}://{self.user}:{self.password}@{self.host}:{self.port}"

logger = logging.getLogger(__name__)

class ProxyManager:
    """Менеджер прокси с поддержкой нескольких провайдеров"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = False
        self.proxies = []
        self.failed_proxies = set()
        self.last_fetch_time = None
        self.multi_provider_manager = None
        
        # SSH туннель для обхода Chrome диалогов
        self.ssh_tunnel_manager = SSHTunnelManager()
        self.tunnel_enabled = config.get('proxy', {}).get('use_ssh_tunnel', True) if config else True
        
        # Прокси управляются автоматически через конфигурацию
        
        proxy_config = config.get('proxy', {}) if config else {}
        
        # Используем только Proxy6 провайдер
        if proxy_config.get('enabled', True):
            logger.info("🌐 Initializing Proxy6-only mode")
            self._init_proxy6_only(proxy_config)
        else:
            logger.info("🌐 ProxyManager initialized in direct mode (no proxy)")
    
    def _init_proxy6_only(self, proxy_config: Dict[str, Any]):
        """Инициализация встроенной Proxy6 логики"""
        try:
            self.api_key = proxy_config.get('api_key')
            self.country = proxy_config.get('country', 'ru')
            self.base_url = "https://px6.link/api"
            self.enabled = True
            
            logger.info("✅ Built-in Proxy6 manager initialized")
            logger.info("🏆 Using Proxy6.net static proxies")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Proxy6 logic: {e}")
            self.enabled = False
    
    def _init_legacy_mode(self, proxy_config: Dict[str, Any]):
        """Инициализация старого режима (только Proxy6)"""
        self.enabled = True
        self.api_key = proxy_config.get('api_key')
        self.country = proxy_config.get('country', 'ru')
        self.base_url = "https://px6.link/api"
        logger.info("🌐 Legacy ProxyManager initialized with Proxy6.net API")
    
    async def get_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Получить рабочий прокси для использования
        
        Returns:
            None для прямого соединения или словарь с данными прокси
        """
        if not self.enabled:
            logger.debug("🌐 Using direct connection (proxy disabled)")
            return None
        
        # Используем Proxy6 провайдер с SSH туннелем
        if hasattr(self, 'proxy6_provider'):
            try:
                proxies = await self.proxy6_provider.get_proxies()
                if proxies:
                    proxy_info = proxies[0]  # Берем первый (и единственный) прокси
                    
                    # Создаем SSH туннель для обхода Chrome диалогов
                    if self.tunnel_enabled:
                        logger.info("🔧 Creating SSH tunnel to bypass Chrome auth dialogs...")
                        try:
                            proxy_creds = ProxyCredentials(
                                host=proxy_info.ip,
                                port=int(proxy_info.port),
                                username=proxy_info.user,
                                password=proxy_info.password,
                                proxy_type=proxy_info.type
                            )
                            
                            tunnel_host, tunnel_port = await self.ssh_tunnel_manager.create_tunnel(proxy_creds)
                            
                            # Возвращаем локальный туннель без авторизации
                            tunnel_dict = {
                                'ip': tunnel_host,
                                'port': str(tunnel_port),
                                'user': '',  # Без авторизации!
                                'pass': '',  # Без авторизации!
                                'type': 'http',  # Локальный HTTP прокси
                                'country': proxy_info.country,
                                'provider': 'ssh_tunnel',
                                'original_proxy': {
                                    'ip': proxy_info.ip,
                                    'port': proxy_info.port,
                                    'user': proxy_info.user,
                                    'type': proxy_info.type
                                }
                            }
                            
                            logger.info(f"✅ SSH tunnel created: {tunnel_host}:{tunnel_port} -> {proxy_info.ip}:{proxy_info.port}")
                            return tunnel_dict
                            
                        except Exception as tunnel_error:
                            logger.warning(f"⚠️ SSH tunnel failed: {tunnel_error}, falling back to direct proxy")
                            # Fallback к прямому прокси
                    
                    # Fallback: обычный прокси (может потребовать диалог)
                    proxy_dict = {
                        'ip': proxy_info.ip,
                        'port': proxy_info.port,
                        'user': proxy_info.user,
                        'pass': proxy_info.password,
                        'type': proxy_info.type,
                        'country': proxy_info.country,
                        'provider': 'proxy6'
                    }
                    
                    logger.warning("⚠️ Using direct proxy (may show Chrome auth dialog)")
                    return proxy_dict
                else:
                    logger.warning("⚠️ No Proxy6 proxies available")
                    return None
            except Exception as e:
                logger.error(f"❌ Proxy6 provider failed: {e}")
                return None
        
        # Legacy режим (старый код Proxy6)
        return await self._get_legacy_proxy()
    
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
        
        # Используем Proxy6 провайдер
        if hasattr(self, 'proxy6_provider'):
            try:
                proxy_key = f"{ip}:{port}"
                self.proxy6_provider._failed_proxies.add(proxy_key)
                logger.warning(f"⚠️ Proxy6: Proxy {ip}:{port} marked as failed: {error or 'Unknown error'}")
                return
            except Exception as e:
                logger.error(f"❌ Failed to mark Proxy6 proxy as failed: {e}")
        
        # Legacy режим
        proxy_key = f"{ip}:{port}"
        self.failed_proxies.add(proxy_key)
        
        logger.warning(f"⚠️ Legacy: Proxy {proxy_key} marked as failed: {error or 'Unknown error'}")
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
    
    async def test_multitransfer_access(self, proxy_dict: Dict[str, Any]) -> bool:
        """
        Тестировать доступ к multitransfer.ru через прокси
        
        Args:
            proxy_dict: Словарь с данными прокси
            
        Returns:
            True если доступ работает
        """
        if not self.enabled or not proxy_dict:
            return True  # Прямое соединение всегда считается рабочим
        
        try:
            logger.info(f"🎯 Testing multitransfer.ru access via {proxy_dict['ip']}:{proxy_dict['port']}")
            is_valid, response_time, error = await proxy_validator.validate_multitransfer_access(proxy_dict)
            
            if is_valid:
                logger.info(f"✅ Multitransfer access confirmed: {proxy_dict['ip']}:{proxy_dict['port']} ({response_time:.2f}s)")
                return True
            else:
                logger.warning(f"⚠️ Multitransfer access failed: {proxy_dict['ip']}:{proxy_dict['port']} - {error}")
                await self.mark_proxy_failed(proxy_dict['ip'], proxy_dict['port'], f"Multitransfer access failed: {error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing multitransfer access: {e}")
            return False
    
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
            'api_key_configured': bool(getattr(self, 'api_key', None)),
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
        
        # Останавливаем SSH туннели
        if hasattr(self, 'ssh_tunnel_manager'):
            await self.ssh_tunnel_manager.stop_tunnel()
    
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
            
            # Проверяем что мы в legacy режиме
            if not hasattr(self, 'base_url') or not hasattr(self, 'api_key'):
                logger.warning("⚠️ Not in legacy mode, skipping API fetch")
                return
            
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
                                    # Пробуем разные возможные названия полей для учетных данных
                                    proxy_user = (proxy_info.get('user') or 
                                                 proxy_info.get('username') or 
                                                 proxy_info.get('login', ''))
                                    proxy_pass = (proxy_info.get('pass') or 
                                                 proxy_info.get('password') or 
                                                 proxy_info.get('pwd', ''))
                                    
                                    proxy_data = {
                                        'id': proxy_info.get('id', proxy_id),
                                        'ip': proxy_info.get('ip', proxy_info.get('host', '')),
                                        'port': str(proxy_info.get('port', '')),
                                        'user': proxy_user,
                                        'pass': proxy_pass,
                                        'country': proxy_info.get('country', 'ru'),
                                        'type': proxy_info.get('type', 'http'),
                                        'date_end': proxy_info.get('date_end', ''),
                                        'active': proxy_info.get('active', '0') == '1'  # Строка!
                                    }
                                    
                                    # DEBUG: Логируем учетные данные для диагностики
                                    logger.debug(f"🔍 Proxy {proxy_data['ip']} credentials: user='{proxy_user}', pass='{proxy_pass[:3]}***'")
                                    
                                    # Предупреждаем если учетные данные отсутствуют
                                    if not proxy_user or not proxy_pass:
                                        logger.warning(f"⚠️ Proxy {proxy_data['ip']} missing credentials - user: '{proxy_user}', pass: '{proxy_pass[:3] if proxy_pass else 'empty'}***'")
                                    
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
    
    async def _get_legacy_proxy(self) -> Optional[Dict[str, Any]]:
        """Legacy метод получения прокси (старый Proxy6 код)"""
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
        logger.info(f"🌐 Using legacy proxy: {proxy['ip']}:{proxy['port']} ({proxy['country']})")
        return proxy



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