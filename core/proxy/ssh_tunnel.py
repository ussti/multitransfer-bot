import asyncio
import subprocess
import socket
import logging
import aiohttp
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProxyCredentials:
    host: str
    port: int
    username: str
    password: str
    proxy_type: str = "http"

class SSHTunnelManager:
    """
    SSH Tunnel Manager for bypassing Chrome system auth dialogs
    Creates local proxy without authentication
    
    STATUS: EXPERIMENTAL (не используется в продакшене)
    - HTTP прокси работает
    - HTTPS CONNECT требует доработки  
    - Основное решение: Chrome Extension (стабильное)
    - Включить: config.yml -> proxy.use_ssh_tunnel: true
    """
    
    def __init__(self):
        self.tunnel_process: Optional[subprocess.Popen] = None
        self.local_port: Optional[int] = None
        self.is_active = False
        self._active_tunnels: Dict[str, subprocess.Popen] = {}
    
    def find_free_port(self) -> int:
        """Find a free local port for tunnel"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    async def create_tunnel(self, proxy_creds: ProxyCredentials) -> Tuple[str, int]:
        """
        Create tunnel using Python HTTP proxy server
        Returns local proxy endpoint without auth
        """
        try:
            self.local_port = self.find_free_port()
            
            # Create Python-based proxy server
            await self._start_proxy_server(proxy_creds)
            
            # Test tunnel
            if await self.test_tunnel("127.0.0.1", self.local_port):
                logger.info(f"✅ SSH tunnel successful: localhost:{self.local_port}")
                return "127.0.0.1", self.local_port
            else:
                raise Exception("Tunnel test failed")
                
        except Exception as e:
            logger.error(f"❌ SSH tunnel creation failed: {e}")
            raise
    
    async def _start_proxy_server(self, proxy_creds: ProxyCredentials):
        """Start local proxy server that forwards to upstream proxy"""
        from aiohttp import web, ClientSession, ClientTimeout
        import base64
        
        # Сохраняем классы для использования в обработчиках
        self._ClientSession = ClientSession
        self._ClientTimeout = ClientTimeout
        self._web = web
        
        # Create auth header for upstream proxy
        auth_string = f"{proxy_creds.username}:{proxy_creds.password}"
        auth_header = base64.b64encode(auth_string.encode()).decode()
        
        async def proxy_handler(request):
            """Handle proxy requests"""
            try:
                # Extract target URL
                if request.method == 'CONNECT':
                    # HTTPS tunnel
                    return await self._handle_connect(request, proxy_creds, auth_header)
                else:
                    # HTTP request
                    return await self._handle_http(request, proxy_creds, auth_header)
                    
            except Exception as e:
                logger.error(f"Proxy handler error: {e}")
                return self._web.Response(status=500, text=str(e))
        
        # Create web app
        app = web.Application()
        app.router.add_route('*', '/{path:.*}', proxy_handler)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.local_port)
        await site.start()
        
        self.is_active = True
        logger.info(f"🔄 Proxy server started on localhost:{self.local_port}")
    
    async def _handle_connect(self, request, proxy_creds, auth_header):
        """Handle HTTPS CONNECT requests"""
        try:
            # Извлекаем целевой хост и порт из URL
            target = str(request.url).replace('http://', '')
            if ':' not in target:
                target += ':443'  # Добавляем порт по умолчанию для HTTPS
            
            logger.debug(f"CONNECT request to: {target}")
            
            # Для простоты возвращаем успешный ответ
            # В реальной реализации нужно создать TCP туннель
            return self._web.Response(
                status=200, 
                text="Connection established",
                headers={'Connection': 'close'}
            )
        except Exception as e:
            logger.error(f"CONNECT handler error: {e}")
            return self._web.Response(status=502, text="Bad Gateway")
    
    async def _handle_http(self, request, proxy_creds, auth_header):
        """Handle HTTP requests through upstream proxy"""
        try:
            upstream_url = f"http://{proxy_creds.host}:{proxy_creds.port}"
            
            headers = dict(request.headers)
            headers['Proxy-Authorization'] = f'Basic {auth_header}'
            
            # Убираем проблемные заголовки
            headers.pop('Host', None)
            headers.pop('Connection', None)
            
            async with self._ClientSession() as session:
                async with session.request(
                    method=request.method,
                    url=str(request.url),
                    headers=headers,
                    data=await request.read(),
                    proxy=upstream_url,
                    timeout=self._ClientTimeout(total=30),
                    allow_redirects=False
                ) as resp:
                    body = await resp.read()
                    
                    # Фильтруем заголовки ответа
                    filtered_headers = {}
                    for key, value in resp.headers.items():
                        if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                            filtered_headers[key] = value
                    
                    return self._web.Response(
                        status=resp.status,
                        headers=filtered_headers,
                        body=body
                    )
        except Exception as e:
            logger.error(f"HTTP handler error: {e}")
            return self._web.Response(status=502, text=f"Proxy error: {e}")
    
    async def test_tunnel(self, host: str, port: int) -> bool:
        """Test tunnel connectivity"""
        try:
            proxy_url = f"http://{host}:{port}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Tunnel test OK. IP: {data.get('origin')}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Tunnel test failed: {e}")
            return False
    
    async def stop_tunnel(self):
        """Stop all tunnels"""
        if self.tunnel_process and self.tunnel_process.poll() is None:
            self.tunnel_process.terminate()
            try:
                self.tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.tunnel_process.kill()
        
        # Stop all active tunnels
        for tunnel_id, process in self._active_tunnels.items():
            if process.poll() is None:
                process.terminate()
        
        self._active_tunnels.clear()
        self.is_active = False
        self.tunnel_process = None
        self.local_port = None
        
        logger.info("🔴 All tunnels stopped")