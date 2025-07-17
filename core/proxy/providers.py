"""
Proxy6.net API Integration - FIXED VERSION
Full implementation with error handling and rotation
"""

import logging
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ProxyVersion(Enum):
    """Proxy version types"""
    IPV4 = "4"
    IPV4_SHARED = "3" 
    IPV6 = "6"

class ProxyType(Enum):
    """Proxy protocol types"""
    HTTP = "http"
    SOCKS5 = "socks"

class ProxyState(Enum):
    """Proxy states"""
    ACTIVE = "active"
    EXPIRED = "expired"
    EXPIRING = "expiring"
    ALL = "all"

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
        """Get proxy URL for requests"""
        return f"{self.type}://{self.user}:{self.password}@{self.host}:{self.port}"
    
    @property
    def proxy_dict(self) -> Dict[str, str]:
        """Get proxy dictionary for requests"""
        proxy_url = self.proxy_url
        return {
            "http": proxy_url,
            "https": proxy_url
        }

class Proxy6Provider:
    """Proxy6.net API client - FIXED VERSION"""
    
    def __init__(self, api_key: str, session: Optional[aiohttp.ClientSession] = None):
        self.api_key = api_key
        self.base_url = "https://px6.link/api"
        self.session = session
        self._own_session = session is None
        
        # Rate limiting (max 3 requests per second)
        self._last_request_time = 0
        self._min_request_interval = 0.34  # ~3 requests per second
        
        # FIX: Если сессия не передана, создаем временную для тестов
        if self.session is None:
            logger.warning("⚠️ No session provided, will create own session")
        
    async def __aenter__(self):
        if self._own_session:
            # FIX: Создаем сессию с простыми настройками
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'MultiTransfer-Bot/1.0'}
            )
            logger.info("✅ Created new aiohttp session for Proxy6")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and self.session:
            await self.session.close()
            logger.info("🛑 Closed aiohttp session")
    
    async def _rate_limit(self):
        """Ensure rate limiting compliance"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self._min_request_interval:
            wait_time = self._min_request_interval - elapsed
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def _make_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make API request with error handling - FIXED VERSION"""
        await self._rate_limit()
        
        # ИСПРАВЛЕННАЯ ЛОГИКА URL
        if method:
            url = f"{self.base_url}/{self.api_key}/{method}"
        else:
            url = f"{self.base_url}/{self.api_key}"
        
        # FIX: Убедимся что сессия создана
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            logger.info(f"🔗 API URL: {url}")  # Отладка
            logger.debug(f"🌐 Proxy6 API: {method} with params: {params}")
            
            async with self.session.get(url, params=params) as response:
                response_text = await response.text()
                logger.info(f"📥 API Response: {response_text[:200]}")  # Первые 200 символов
                
                if response.status == 429:
                    logger.warning("⚠️ Rate limit exceeded, waiting...")
                    await asyncio.sleep(1)
                    return await self._make_request(method, params)
                
                response.raise_for_status()
                data = await response.json()
                
                if data.get("status") == "no":
                    error_id = data.get("error_id", 0)
                    error_msg = data.get("error", "Unknown error")
                    logger.error(f"❌ Proxy6 API error {error_id}: {error_msg}")
                    raise Proxy6APIError(error_id, error_msg, data)
                
                logger.debug(f"✅ Proxy6 API success: {method}")
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"❌ HTTP error in Proxy6 API: {e}")
            raise Proxy6NetworkError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error in Proxy6 API: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance and info"""
        return await self._make_request("")
    
    async def get_price(self, count: int, period: int, version: ProxyVersion = ProxyVersion.IPV4) -> Dict[str, Any]:
        """Get price information for proxy order"""
        params = {
            "count": count,
            "period": period,
            "version": version.value
        }
        return await self._make_request("getprice", params)
    
    async def get_available_count(self, country: str = "ru", version: ProxyVersion = ProxyVersion.IPV4) -> int:
        """Get available proxy count for country"""
        params = {
            "country": country,
            "version": version.value
        }
        result = await self._make_request("getcount", params)
        return result.get("count", 0)
    
    async def get_countries(self, version: ProxyVersion = ProxyVersion.IPV4) -> List[str]:
        """Get available countries"""
        params = {"version": version.value}
        result = await self._make_request("getcountry", params)
        return result.get("list", [])
    
    async def get_proxies(self, 
                         state: ProxyState = ProxyState.ACTIVE,
                         descr: Optional[str] = None,
                         page: int = 1,
                         limit: int = 1000) -> List[ProxyInfo]:
        """Get list of purchased proxies"""
        params = {
            "state": state.value,
            "page": page,
            "limit": limit
        }
        if descr:
            params["descr"] = descr
        
        result = await self._make_request("getproxy", params)
        proxies = []
        
        proxy_list = result.get("list", {})
        for proxy_id, proxy_data in proxy_list.items():
            proxy_info = ProxyInfo(
                id=proxy_data.get("id", proxy_id),
                ip=proxy_data.get("ip", ""),
                host=proxy_data.get("host", ""),
                port=proxy_data.get("port", ""),
                user=proxy_data.get("user", ""),
                password=proxy_data.get("pass", ""),
                type=proxy_data.get("type", "http"),
                country=proxy_data.get("country", ""),
                date=proxy_data.get("date", ""),
                date_end=proxy_data.get("date_end", ""),
                active=bool(int(proxy_data.get("active", 0)))
            )
            proxies.append(proxy_info)
        
        logger.info(f"📋 Retrieved {len(proxies)} proxies from Proxy6")
        return proxies
    
    async def buy_proxies(self,
                         count: int,
                         period: int,
                         country: str = "ru",
                         version: ProxyVersion = ProxyVersion.IPV4,
                         proxy_type: ProxyType = ProxyType.HTTP,
                         descr: Optional[str] = None) -> List[ProxyInfo]:
        """Buy new proxies"""
        params = {
            "count": count,
            "period": period,
            "country": country,
            "version": version.value,
            "type": proxy_type.value
        }
        if descr:
            params["descr"] = descr
        
        logger.info(f"💰 Buying {count} {country} proxies for {period} days")
        result = await self._make_request("buy", params)
        
        proxies = []
        proxy_list = result.get("list", {})
        for proxy_id, proxy_data in proxy_list.items():
            proxy_info = ProxyInfo(
                id=proxy_data.get("id", proxy_id),
                ip=proxy_data.get("ip", ""),
                host=proxy_data.get("host", ""),
                port=proxy_data.get("port", ""),
                user=proxy_data.get("user", ""),
                password=proxy_data.get("pass", ""),
                type=proxy_data.get("type", "http"),
                country=country,
                date=proxy_data.get("date", ""),
                date_end=proxy_data.get("date_end", ""),
                active=bool(int(proxy_data.get("active", 1)))
            )
            proxies.append(proxy_info)
        
        total_cost = result.get("price", 0)
        logger.info(f"✅ Successfully bought {len(proxies)} proxies for {total_cost} RUB")
        return proxies
    
    async def check_proxy(self, proxy_id: str) -> bool:
        """Check if proxy is working"""
        params = {"ids": proxy_id}
        result = await self._make_request("check", params)
        return result.get("proxy_status", False)
    
    async def delete_proxies(self, proxy_ids: List[str]) -> int:
        """Delete proxies by IDs"""
        params = {"ids": ",".join(proxy_ids)}
        result = await self._make_request("delete", params)
        count = result.get("count", 0)
        logger.info(f"🗑️ Deleted {count} proxies")
        return count
    
    async def prolong_proxies(self, proxy_ids: List[str], period: int) -> Dict[str, Any]:
        """Extend proxy period"""
        params = {
            "ids": ",".join(proxy_ids),
            "period": period
        }
        result = await self._make_request("prolong", params)
        logger.info(f"⏰ Extended {len(proxy_ids)} proxies for {period} days")
        return result


class Proxy6APIError(Exception):
    """Proxy6.net API error"""
    
    def __init__(self, error_id: int, error_message: str, response_data: Dict[str, Any]):
        self.error_id = error_id
        self.error_message = error_message
        self.response_data = response_data
        super().__init__(f"Proxy6 API Error {error_id}: {error_message}")


class Proxy6NetworkError(Exception):
    """Network error when communicating with Proxy6.net"""
    pass


class Proxy6ConfigError(Exception):
    """Configuration error for Proxy6.net"""
    pass


# Error code mappings for better handling
PROXY6_ERROR_CODES = {
    30: "Unknown error",
    100: "Authorization error, wrong API key",
    105: "Wrong IP address or IP restriction",
    110: "Wrong method",
    200: "Wrong proxies quantity",
    210: "Wrong period (days)",
    220: "Wrong country code",
    230: "Wrong proxy IDs format",
    240: "Wrong proxy version",
    250: "Technical description error",
    260: "Wrong proxy type",
    300: "Not enough proxies available",
    400: "Insufficient balance",
    404: "Element not found",
    410: "Price calculation error"
}