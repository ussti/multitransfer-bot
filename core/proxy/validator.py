"""
Proxy Validation and Health Check Utilities
Утилиты для проверки прокси и их работоспособности
"""

import logging
import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class ProxyValidator:
    """Validator for proxy connections"""
    
    def __init__(self):
        self.test_urls = [
            'http://httpbin.org/ip',
            'http://icanhazip.com',
            'https://api.ipify.org'
        ]
        self.timeout = 10  # seconds
    
    async def validate_proxy(self, proxy_info: Dict[str, Any]) -> Tuple[bool, float, Optional[str]]:
        """
        Validate proxy connection and measure response time
        
        Args:
            proxy_info: Dictionary with proxy details (ip, port, user, pass, type)
            
        Returns:
            Tuple of (is_valid, response_time, error_message)
        """
        try:
            start_time = time.time()
            
            # Build proxy URL
            proxy_type = proxy_info.get('type', 'http').lower()
            if proxy_info.get('user') and proxy_info.get('pass'):
                proxy_url = f"{proxy_type}://{proxy_info['user']}:{proxy_info['pass']}@{proxy_info['ip']}:{proxy_info['port']}"
            else:
                proxy_url = f"{proxy_type}://{proxy_info['ip']}:{proxy_info['port']}"
            
            logger.debug(f"🔍 Testing proxy: {proxy_info['ip']}:{proxy_info['port']}")
            
            async with aiohttp.ClientSession() as session:
                for test_url in self.test_urls:
                    try:
                        async with session.get(
                            test_url,
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=self.timeout)
                        ) as response:
                            if response.status == 200:
                                response_time = time.time() - start_time
                                response_text = await response.text()
                                
                                # Check if response contains IP (basic validation)
                                if any(char.isdigit() for char in response_text):
                                    logger.debug(f"✅ Proxy validation successful: {proxy_info['ip']}:{proxy_info['port']} ({response_time:.2f}s)")
                                    return True, response_time, None
                                else:
                                    logger.warning(f"⚠️ Proxy returned invalid response: {response_text[:100]}")
                                    continue
                    except Exception as e:
                        logger.debug(f"⚠️ Test URL {test_url} failed: {e}")
                        continue
                
                # If all test URLs failed
                response_time = time.time() - start_time
                return False, response_time, "All test URLs failed"
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ Proxy validation failed for {proxy_info['ip']}:{proxy_info['port']}: {e}")
            return False, response_time, str(e)
    
    async def validate_multitransfer_access(self, proxy_info: Dict[str, Any]) -> Tuple[bool, float, Optional[str]]:
        """
        Specifically test proxy access to multitransfer.ru
        
        Args:
            proxy_info: Dictionary with proxy details
            
        Returns:
            Tuple of (is_valid, response_time, error_message)
        """
        try:
            start_time = time.time()
            
            # Build proxy URL
            proxy_type = proxy_info.get('type', 'http').lower()
            if proxy_info.get('user') and proxy_info.get('pass'):
                proxy_url = f"{proxy_type}://{proxy_info['user']}:{proxy_info['pass']}@{proxy_info['ip']}:{proxy_info['port']}"
            else:
                proxy_url = f"{proxy_type}://{proxy_info['ip']}:{proxy_info['port']}"
            
            logger.debug(f"🎯 Testing multitransfer.ru access via proxy: {proxy_info['ip']}:{proxy_info['port']}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://multitransfer.ru',
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=15),  # Longer timeout for the main site
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                    }
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        response_text = await response.text()
                        
                        # Check for multitransfer-specific content
                        if 'multitransfer' in response_text.lower() or 'перевод' in response_text.lower():
                            logger.debug(f"✅ Multitransfer access successful: {proxy_info['ip']}:{proxy_info['port']} ({response_time:.2f}s)")
                            return True, response_time, None
                        else:
                            logger.warning(f"⚠️ Multitransfer site returned unexpected content")
                            return False, response_time, "Site content validation failed"
                    else:
                        logger.warning(f"⚠️ Multitransfer returned HTTP {response.status}")
                        return False, response_time, f"HTTP {response.status}"
                        
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"❌ Multitransfer access test failed for {proxy_info['ip']}:{proxy_info['port']}: {error_msg}")
            return False, response_time, error_msg
    
    async def quick_health_check(self, proxy_info: Dict[str, Any]) -> bool:
        """
        Quick health check for proxy (faster, basic connectivity test)
        
        Args:
            proxy_info: Dictionary with proxy details
            
        Returns:
            True if proxy is responding
        """
        try:
            is_valid, response_time, error = await self.validate_proxy(proxy_info)
            return is_valid and response_time < 5.0  # Under 5 seconds is considered healthy
        except:
            return False

# Create global validator instance
proxy_validator = ProxyValidator()