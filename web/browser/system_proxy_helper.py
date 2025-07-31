"""
Системный помощник для настройки прокси macOS
"""
import subprocess
import logging
import asyncio
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SystemProxyManager:
    """Управление системными настройками прокси macOS"""
    
    def __init__(self):
        self.original_settings = {}
        self.is_configured = False
    
    async def configure_proxy(self, proxy_config: Dict[str, str]) -> bool:
        """
        Настроить системный прокси (HTTP или SOCKS)
        
        Args:
            proxy_config: Конфигурация прокси (ip, port, user, pass, type)
            
        Returns:
            True если настройка успешна
        """
        try:
            # Сохраняем текущие настройки
            await self._save_current_settings()
            
            # Настраиваем прокси в зависимости от типа
            ip = proxy_config['ip']
            port = proxy_config['port']
            user = proxy_config.get('user', '')
            password = proxy_config.get('pass', '')
            proxy_type = proxy_config.get('type', 'http').lower()
            
            logger.info(f"🔧 Configuring system {proxy_type.upper()} proxy: {ip}:{port}")
            
            if proxy_type == 'socks5':
                # Настраиваем SOCKS прокси для Wi-Fi
                cmd = [
                    'networksetup', '-setsocksfirewallproxy', 'Wi-Fi', 
                    ip, port
                ]
                
                if user and password:
                    cmd.extend([user, password])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"❌ Failed to set SOCKS proxy: {result.stderr}")
                    return False
                
                # Включаем SOCKS прокси
                result = subprocess.run([
                    'networksetup', '-setsocksfirewallproxystate', 'Wi-Fi', 'on'
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"❌ Failed to enable SOCKS proxy: {result.stderr}")
                    return False
                    
            else:  # HTTP прокси
                # Настраиваем HTTP прокси для Wi-Fi
                cmd = [
                    'networksetup', '-setwebproxy', 'Wi-Fi', 
                    ip, port
                ]
                
                if user and password:
                    cmd.extend([user, password])
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"❌ Failed to set HTTP proxy: {result.stderr}")
                    return False
                
                # Включаем HTTP прокси
                result = subprocess.run([
                    'networksetup', '-setwebproxystate', 'Wi-Fi', 'on'
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"❌ Failed to enable HTTP proxy: {result.stderr}")
                    return False
                
                # Также настраиваем HTTPS прокси
                subprocess.run([
                    'networksetup', '-setsecurewebproxy', 'Wi-Fi', 
                    ip, port, user, password
                ] if user and password else [
                    'networksetup', '-setsecurewebproxy', 'Wi-Fi', 
                    ip, port
                ])
                
                subprocess.run([
                    'networksetup', '-setsecurewebproxystate', 'Wi-Fi', 'on'
                ])
            
            self.is_configured = True
            logger.info(f"✅ System {proxy_type.upper()} proxy configured successfully")
            
            # Небольшая задержка для применения настроек
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error configuring system proxy: {e}")
            return False
    
    async def restore_settings(self):
        """Восстановить оригинальные настройки прокси"""
        if not self.is_configured:
            return
        
        try:
            logger.info("🔄 Restoring original proxy settings...")
            
            # Отключаем все типы прокси
            subprocess.run([
                'networksetup', '-setsocksfirewallproxystate', 'Wi-Fi', 'off'
            ], capture_output=True)
            
            subprocess.run([
                'networksetup', '-setwebproxystate', 'Wi-Fi', 'off'
            ], capture_output=True)
            
            subprocess.run([
                'networksetup', '-setsecurewebproxystate', 'Wi-Fi', 'off'
            ], capture_output=True)
            
            logger.info("✅ Original proxy settings restored")
            self.is_configured = False
            
        except Exception as e:
            logger.error(f"❌ Error restoring proxy settings: {e}")
    
    async def _save_current_settings(self):
        """Сохранить текущие настройки прокси"""
        try:
            result = subprocess.run([
                'networksetup', '-getsocksfirewallproxy', 'Wi-Fi'
            ], capture_output=True, text=True)
            
            self.original_settings['socks'] = result.stdout
            logger.debug(f"💾 Saved original SOCKS settings: {result.stdout}")
            
        except Exception as e:
            logger.error(f"❌ Error saving current settings: {e}")
    
    async def test_proxy_connection(self, proxy_config: Dict[str, str]) -> bool:
        """
        Тестировать подключение к прокси
        
        Args:
            proxy_config: Конфигурация прокси
            
        Returns:
            True если прокси работает
        """
        try:
            # Простой тест через curl с прокси
            proxy_type = proxy_config.get('type', 'http').lower()
            if proxy_type == 'socks5':
                proxy_url = f"socks5://{proxy_config['user']}:{proxy_config['pass']}@{proxy_config['ip']}:{proxy_config['port']}"
            else:
                proxy_url = f"http://{proxy_config['user']}:{proxy_config['pass']}@{proxy_config['ip']}:{proxy_config['port']}"
            
            result = subprocess.run([
                'curl', '--connect-timeout', '10', '--proxy', proxy_url,
                'http://httpbin.org/ip'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                logger.info(f"✅ Proxy connection test successful: {result.stdout[:100]}")
                return True
            else:
                logger.warning(f"⚠️ Proxy connection test failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing proxy connection: {e}")
            return False

# Глобальный экземпляр для управления
system_proxy_manager = SystemProxyManager()