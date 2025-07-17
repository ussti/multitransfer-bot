"""
Browser Manager with Proxy Integration and Anti-Captcha Plugin Support - COMPLETE VERSION
Handles Chrome WebDriver lifecycle with proxy rotation, error recovery, and captcha solving
Supports both headless (with Xvfb) and non-headless modes for production
"""

import asyncio
import logging
import random
import time
import os
import subprocess
import platform
from typing import Optional, List, Dict, Any

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from core.proxy.manager import ProxyManager
from core.proxy.providers import ProxyInfo

logger = logging.getLogger(__name__)

class BrowserManager:
    """Browser manager with proxy support, fallback capabilities, and Anti-Captcha plugin"""
    
    def __init__(self, config: Dict[str, Any], proxy_manager: Optional[ProxyManager] = None):
        self.config = config
        self.proxy_manager = proxy_manager
        
        # Browser settings
        browser_config = config.get('browser', {})
        self.headless = browser_config.get('headless', True)
        self.window_size = browser_config.get('window_size', '1920,1080')
        self.page_load_timeout = browser_config.get('page_load_timeout', 30)
        self.implicit_wait = browser_config.get('implicit_wait', 10)
        self.user_agents = browser_config.get('user_agents', [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ])
        
        # Captcha settings
        captcha_config = config.get('captcha', {})
        self.captcha_plugin_enabled = captcha_config.get('plugin_enabled', True)
        self.captcha_plugin_path = captcha_config.get('plugin_path', 'plugins')
        self.captcha_api_key = captcha_config.get('api_key')
        
        # Production settings
        self.environment = config.get('railway', {}).get('environment', 'development')
        self.use_xvfb = self.environment == 'production' and self.headless and self.captcha_plugin_enabled
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 2
        
        # Browser instance
        self.driver = None
        self.current_proxy = None
        self.fallback_mode = False
        self.plugin_loaded = False
        self.xvfb_display = None
        
        logger.info("🔧 BrowserManager initialized with proxy and captcha plugin support")
        logger.info(f"🌍 Environment: {self.environment}")
        logger.info(f"📺 Xvfb mode: {self.use_xvfb}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    def _check_plugin_availability(self) -> bool:
        """Check if Anti-Captcha plugin is available"""
        if not self.captcha_plugin_enabled:
            return False
        
        plugin_path = os.path.abspath(self.captcha_plugin_path)
        manifest_path = os.path.join(plugin_path, "manifest.json")
        config_path = os.path.join(plugin_path, "js", "config_ac_api_key.js")
        
        if os.path.exists(manifest_path) and os.path.exists(config_path):
            logger.info(f"✅ Anti-Captcha plugin found: {plugin_path}")
            
            # Check if API key is configured
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_content = f.read()
                    if "antiCapthaPredefinedApiKey = ''" in config_content:
                        logger.warning("⚠️ API key not configured in plugin config file!")
                        logger.info("💡 Edit: plugins/js/config_ac_api_key.js")
                        return False
                    else:
                        logger.info("✅ API key configured in plugin")
                        return True
            except Exception as e:
                logger.warning(f"⚠️ Could not read plugin config: {e}")
                return False
        else:
            logger.warning(f"⚠️ Anti-Captcha plugin not found: {plugin_path}")
            logger.info("💡 Expected structure:")
            logger.info("   plugins/manifest.json")
            logger.info("   plugins/js/config_ac_api_key.js")
            return False
    
    async def _setup_xvfb(self) -> bool:
        """Setup Xvfb for headless plugin support in production"""
        if not self.use_xvfb:
            return True
        
        try:
            logger.info("🖥️ Setting up Xvfb for headless plugin support...")
            
            # Check if Xvfb is available
            result = subprocess.run(['which', 'xvfb-run'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("❌ Xvfb not found. Install with: apt-get install -y xvfb")
                return False
            
            # Set display variable
            display_num = random.randint(10, 99)
            self.xvfb_display = f":{display_num}"
            os.environ['DISPLAY'] = self.xvfb_display
            
            # Start Xvfb server
            xvfb_cmd = [
                'Xvfb', 
                self.xvfb_display,
                '-screen', '0', '1920x1080x24',
                '-ac',
                '+extension', 'GLX',
                '+render',
                '-noreset'
            ]
            
            self.xvfb_process = subprocess.Popen(
                xvfb_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for Xvfb to start
            await asyncio.sleep(2)
            
            # Check if Xvfb is running
            if self.xvfb_process.poll() is None:
                logger.info(f"✅ Xvfb started successfully on display {self.xvfb_display}")
                return True
            else:
                logger.error("❌ Xvfb failed to start")
                return False
                
        except Exception as e:
            logger.error(f"❌ Xvfb setup error: {e}")
            return False
    
    async def start_browser(self, use_proxy: bool = True) -> bool:
        """Start browser with optional proxy and Anti-Captcha plugin"""
        
        # Setup Xvfb if needed
        if self.use_xvfb:
            xvfb_success = await self._setup_xvfb()
            if not xvfb_success:
                logger.warning("⚠️ Xvfb setup failed, falling back to API-only captcha solving")
                self.captcha_plugin_enabled = False
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 Browser start attempt {attempt + 1}/{self.max_retries}")
                
                # Get proxy if available and requested
                proxy = None
                if use_proxy and self.proxy_manager:
                    proxy = await self.proxy_manager.get_working_proxy()
                    if proxy:
                        logger.info(f"🌐 Using proxy: {proxy.host}:{proxy.port}")
                        self.current_proxy = proxy
                        self.fallback_mode = False
                    else:
                        logger.warning("⚠️ No proxy available, starting in direct mode")
                        self.fallback_mode = True
                else:
                    logger.info("🔧 Starting browser in direct mode (no proxy requested)")
                    self.fallback_mode = True
                
                # Create Chrome options with plugin support
                chrome_options = self._create_chrome_options(proxy)
                
                # Create driver
                self.driver = uc.Chrome(options=chrome_options)
                self.driver.implicitly_wait(self.implicit_wait)
                self.driver.set_page_load_timeout(self.page_load_timeout)
                
                # Configure Anti-Captcha plugin if loaded
                if self.plugin_loaded:
                    await self._configure_anticaptcha_plugin()
                
                # Test browser connection
                test_success = await self._test_browser_connection()
                if test_success:
                    mode = "proxy" if proxy else "direct"
                    plugin_status = "with plugin" if self.plugin_loaded else "without plugin"
                    display_mode = f"Xvfb({self.xvfb_display})" if self.use_xvfb else ("headless" if self.headless else "windowed")
                    logger.info(f"✅ Browser started successfully in {mode} mode {plugin_status} ({display_mode})")
                    return True
                else:
                    logger.warning(f"⚠️ Browser connection test failed")
                    await self._cleanup_browser()
                    
            except Exception as e:
                logger.error(f"❌ Browser start attempt {attempt + 1} failed: {e}")
                await self._cleanup_browser()
                
                # Mark proxy as failed if we were using one
                if proxy and self.proxy_manager:
                    await self.proxy_manager.mark_proxy_result(proxy.id, False)
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"⏰ Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        logger.error(f"❌ Failed to start browser after {self.max_retries} attempts")
        return False
    
    def _create_chrome_options(self, proxy: Optional[ProxyInfo] = None) -> Options:
        """Create Chrome options with proxy, stealth settings, and Anti-Captcha plugin"""
        chrome_options = Options()
        
        # Basic browser settings
        # In production with Xvfb, we run non-headless for plugin support
        if self.headless and not self.use_xvfb:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"--window-size={self.window_size}")
        
        # User agent
        user_agent = random.choice(self.user_agents)
        chrome_options.add_argument(f"--user-agent={user_agent}")
        
        # Proxy configuration
        if proxy:
            if proxy.type == "http":
                chrome_options.add_argument(f"--proxy-server=http://{proxy.host}:{proxy.port}")
            elif proxy.type == "socks":
                chrome_options.add_argument(f"--proxy-server=socks5://{proxy.host}:{proxy.port}")
        
        # Anti-Captcha plugin configuration
        if self._check_plugin_availability():
            try:
                plugin_path = os.path.abspath(self.captcha_plugin_path)
                
                # CORRECT way to load plugin in Selenium
                chrome_options.add_argument(f"--disable-extensions-except={plugin_path}")
                chrome_options.add_argument(f"--load-extension={plugin_path}")
                
                # Additional flags for plugin compatibility
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
                chrome_options.add_argument("--allow-running-insecure-content")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--disable-infobars")
                chrome_options.add_argument("--disable-background-timer-throttling")
                chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                chrome_options.add_argument("--disable-renderer-backgrounding")
                
                # REMOVE PROBLEMATIC OPTIONS FOR MACOS
                # These options cause issues with undetected-chromedriver on macOS
                # chrome_options.add_experimental_option("excludeSwitches", ["--disable-extensions", "--enable-automation"])
                # chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # Alternative approach - use prefs instead
                prefs = {
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.default_content_settings.popups": 0,
                    "profile.managed_default_content_settings.images": 2
                }
                chrome_options.add_experimental_option("prefs", prefs)
                
                # Production-specific settings
                if self.environment == 'production':
                    chrome_options.add_argument("--disable-logging")
                    chrome_options.add_argument("--disable-gpu-logging")
                    chrome_options.add_argument("--silent")
                    chrome_options.add_argument("--disable-default-apps")
                    chrome_options.add_argument("--disable-sync")
                
                self.plugin_loaded = True
                logger.info("🔌 Anti-Captcha plugin loaded into Chrome (macOS compatible)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load Anti-Captcha plugin: {e}")
                self.plugin_loaded = False
        else:
            self.plugin_loaded = False
        
        return chrome_options
    
    async def _configure_anticaptcha_plugin(self) -> bool:
        """Configure Anti-Captcha plugin after browser startup"""
        if not self.plugin_loaded or not self.captcha_api_key:
            return False
        
        try:
            logger.info("🔧 Configuring Anti-Captcha plugin...")
            
            # Wait for plugin to initialize
            await asyncio.sleep(3)
            
            # Configure plugin via JavaScript
            config_script = f"""
            // Wait for plugin to load
            var attempts = 0;
            var maxAttempts = 10;
            
            function configurePlugin() {{
                // Check for different plugin object names
                var pluginObj = window.AntiCaptcha || 
                               window.antiCaptchaPlugin || 
                               window.anticaptcha ||
                               window.AC;
                
                if (pluginObj) {{
                    try {{
                        // Configure API key
                        if (typeof pluginObj.setAPIKey === 'function') {{
                            pluginObj.setAPIKey('{self.captcha_api_key}');
                        }}
                        
                        // Enable automatic solving
                        if (typeof pluginObj.setAutoSolveEnabled === 'function') {{
                            pluginObj.setAutoSolveEnabled(true);
                        }}
                        
                        // Set solve timeout
                        if (typeof pluginObj.setTimeout === 'function') {{
                            pluginObj.setTimeout(120);
                        }}
                        
                        // Enable debug mode for development
                        if (typeof pluginObj.setDebugEnabled === 'function') {{
                            pluginObj.setDebugEnabled(true);
                        }}
                        
                        console.log('Anti-Captcha plugin configured successfully');
                        return 'plugin_configured_success';
                    }} catch (e) {{
                        console.error('Anti-Captcha plugin configuration error:', e);
                        return 'plugin_configured_error';
                    }}
                }} else {{
                    attempts++;
                    if (attempts < maxAttempts) {{
                        setTimeout(configurePlugin, 1000);
                        return 'plugin_waiting';
                    }} else {{
                        console.error('Anti-Captcha plugin not detected after', maxAttempts, 'attempts');
                        return 'plugin_not_found';
                    }}
                }}
            }}
            
            return configurePlugin();
            """
            
            # Execute configuration
            result = self.driver.execute_script(config_script)
            
            # Wait for configuration to complete
            max_wait = 15  # seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    check_result = self.driver.execute_script("""
                        var pluginObj = window.AntiCaptcha || 
                                       window.antiCaptchaPlugin || 
                                       window.anticaptcha ||
                                       window.AC;
                        return pluginObj ? 'plugin_ready' : 'plugin_not_ready';
                    """)
                    if check_result == 'plugin_ready':
                        logger.info("✅ Anti-Captcha plugin configured and ready")
                        return True
                    await asyncio.sleep(1)
                except:
                    await asyncio.sleep(1)
            
            logger.warning("⚠️ Anti-Captcha plugin configuration timeout")
            return False
            
        except Exception as e:
            logger.error(f"❌ Anti-Captcha plugin configuration error: {e}")
            return False
    
    async def _test_browser_connection(self) -> bool:
        """Test browser connection and functionality"""
        try:
            if not self.driver:
                return False
            
            # Test basic navigation
            logger.debug("🧪 Testing browser connection...")
            start_time = time.time()
            
            # Try to navigate to a test page
            test_url = "https://httpbin.org/ip"
            self.driver.get(test_url)
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Check if we got a response
            page_source = self.driver.page_source.lower()
            if "origin" in page_source or "ip" in page_source:
                response_time = time.time() - start_time
                logger.debug(f"✅ Browser connection test passed ({response_time:.2f}s)")
                
                # Mark proxy as successful if we used one
                if self.current_proxy and self.proxy_manager:
                    await self.proxy_manager.mark_proxy_result(self.current_proxy.id, True, response_time)
                
                return True
            else:
                logger.warning("⚠️ Browser connection test failed - no expected content")
                return False
                
        except Exception as e:
            logger.error(f"❌ Browser connection test error: {e}")
            return False
    
    async def navigate_to_url(self, url: str, timeout: int = 30) -> bool:
        """Navigate to URL with error handling"""
        try:
            if not self.driver:
                logger.error("❌ No browser driver available")
                return False
            
            logger.info(f"🌐 Navigating to: {url}")
            start_time = time.time()
            
            self.driver.get(url)
            
            # Wait for page load
            await asyncio.sleep(3)
            
            # Check if navigation was successful
            current_url = self.driver.current_url
            if current_url and not current_url.startswith("data:"):
                response_time = time.time() - start_time
                logger.info(f"✅ Navigation successful ({response_time:.2f}s)")
                
                # Mark proxy as successful if we used one
                if self.current_proxy and self.proxy_manager:
                    await self.proxy_manager.mark_proxy_result(self.current_proxy.id, True, response_time)
                
                return True
            else:
                logger.error(f"❌ Navigation failed - current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Navigation error: {e}")
            
            # Mark proxy as failed if we used one
            if self.current_proxy and self.proxy_manager:
                await self.proxy_manager.mark_proxy_result(self.current_proxy.id, False)
            
            return False
    
    async def wait_for_element(self, by: By, value: str, timeout: int = 10) -> bool:
        """Wait for element to be present"""
        try:
            if not self.driver:
                return False
            
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            return element is not None
            
        except TimeoutException:
            logger.debug(f"⏰ Element not found within {timeout}s: {value}")
            return False
        except Exception as e:
            logger.error(f"❌ Error waiting for element: {e}")
            return False
    
    async def find_element_safe(self, by: By, value: str) -> Optional[Any]:
        """Find element safely without throwing exceptions"""
        try:
            if not self.driver:
                return None
            
            return self.driver.find_element(by, value)
            
        except Exception as e:
            logger.debug(f"🔍 Element not found: {value} ({e})")
            return None
    
    async def find_elements_safe(self, by: By, value: str) -> List[Any]:
        """Find elements safely without throwing exceptions"""
        try:
            if not self.driver:
                return []
            
            return self.driver.find_elements(by, value)
            
        except Exception as e:
            logger.debug(f"🔍 Elements not found: {value} ({e})")
            return []
    
    async def click_element_safe(self, element) -> bool:
        """Click element safely with error handling"""
        try:
            if not element:
                return False
            
            # Scroll to element first
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            await asyncio.sleep(0.5)
            
            # Try to click
            element.click()
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.debug(f"❌ Click failed: {e}")
            return False
    
    async def type_text_safe(self, element, text: str) -> bool:
        """Type text safely with error handling"""
        try:
            if not element or not text:
                return False
            
            # Clear field first
            element.clear()
            await asyncio.sleep(0.2)
            
            # Type text
            element.send_keys(text)
            await asyncio.sleep(0.2)
            
            return True
            
        except Exception as e:
            logger.debug(f"❌ Type text failed: {e}")
            return False
    
    async def get_page_source(self) -> str:
        """Get page source safely"""
        try:
            if not self.driver:
                return ""
            
            return self.driver.page_source
            
        except Exception as e:
            logger.error(f"❌ Failed to get page source: {e}")
            return ""
    
    async def take_screenshot(self, filename: str = None) -> bool:
        """Take screenshot for debugging"""
        try:
            if not self.driver:
                return False
            
            if not filename:
                timestamp = int(time.time())
                filename = f"logs/automation/screenshot_{timestamp}.png"
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            success = self.driver.save_screenshot(filename)
            if success:
                logger.info(f"📸 Screenshot saved: {filename}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Screenshot failed: {e}")
            return False
    
    async def restart_browser(self) -> bool:
        """Restart browser (useful for proxy rotation)"""
        try:
            logger.info("🔄 Restarting browser...")
            
            # Close current browser
            await self._cleanup_browser()
            
            # Start new browser
            success = await self.start_browser(use_proxy=True)
            
            if success:
                logger.info("✅ Browser restarted successfully")
            else:
                logger.error("❌ Browser restart failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Browser restart error: {e}")
            return False
    
    async def switch_proxy(self) -> bool:
        """Switch to a different proxy"""
        try:
            if not self.proxy_manager:
                logger.warning("⚠️ No proxy manager available for switching")
                return False
            
            logger.info("🔄 Switching proxy...")
            
            # Mark current proxy as failed if we have one
            if self.current_proxy:
                await self.proxy_manager.mark_proxy_result(self.current_proxy.id, False)
            
            # Restart browser with new proxy
            success = await self.restart_browser()
            
            if success:
                logger.info("✅ Proxy switched successfully")
            else:
                logger.error("❌ Proxy switch failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Proxy switch error: {e}")
            return False
    
    async def _cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.plugin_loaded = False
                logger.debug("🧹 Browser cleaned up")
        except Exception as e:
            logger.debug(f"🧹 Browser cleanup error: {e}")
    
    async def _cleanup_xvfb(self):
        """Clean up Xvfb resources"""
        try:
            if hasattr(self, 'xvfb_process') and self.xvfb_process:
                self.xvfb_process.terminate()
                self.xvfb_process.wait()
                logger.debug("🧹 Xvfb cleaned up")
        except Exception as e:
            logger.debug(f"🧹 Xvfb cleanup error: {e}")
    
    async def close(self):
        """Close browser and clean up resources"""
        logger.info("🛑 Closing browser...")
        await self._cleanup_browser()
        await self._cleanup_xvfb()
        self.current_proxy = None
        self.fallback_mode = False
    
    def is_alive(self) -> bool:
        """Check if browser is still alive"""
        try:
            if not self.driver:
                return False
            
            # Try to get current URL
            current_url = self.driver.current_url
            return current_url is not None
            
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get browser status information"""
        return {
            "is_alive": self.is_alive(),
            "fallback_mode": self.fallback_mode,
            "plugin_loaded": self.plugin_loaded,
            "xvfb_mode": self.use_xvfb,
            "xvfb_display": self.xvfb_display,
            "current_proxy": {
                "id": self.current_proxy.id if self.current_proxy else None,
                "host": self.current_proxy.host if self.current_proxy else None,
                "port": self.current_proxy.port if self.current_proxy else None
            } if self.current_proxy else None,
            "headless": self.headless,
            "window_size": self.window_size,
            "captcha_plugin_enabled": self.captcha_plugin_enabled,
            "captcha_plugin_available": self._check_plugin_availability(),
            "environment": self.environment
        }
    
    # Keep all existing utility methods
    async def enable_javascript(self):
        """Enable JavaScript (useful for specific sites)"""
        try:
            if not self.driver:
                return False
            
            # Execute JavaScript to enable it
            self.driver.execute_script("return navigator.userAgent;")
            logger.debug("🔧 JavaScript enabled")
            return True
            
        except Exception as e:
            logger.debug(f"⚠️ JavaScript enable failed: {e}")
            return False
    
    async def handle_alert(self, accept: bool = True) -> bool:
        """Handle JavaScript alerts/popups"""
        try:
            if not self.driver:
                return False
            
            alert = self.driver.switch_to.alert
            if accept:
                alert.accept()
            else:
                alert.dismiss()
            
            logger.debug("🚨 Alert handled")
            return True
            
        except Exception as e:
            logger.debug(f"🚨 No alert to handle: {e}")
            return False
    
    async def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript code"""
        try:
            if not self.driver:
                return None
            
            return self.driver.execute_script(script, *args)
            
        except Exception as e:
            logger.debug(f"❌ Script execution failed: {e}")
            return None
    
    async def get_element_text(self, element) -> str:
        """Get element text safely"""
        try:
            if not element:
                return ""
            
            return element.text or ""
            
        except Exception as e:
            logger.debug(f"❌ Failed to get element text: {e}")
            return ""
    
    async def get_element_attribute(self, element, attribute: str) -> str:
        """Get element attribute safely"""
        try:
            if not element:
                return ""
            
            return element.get_attribute(attribute) or ""
            
        except Exception as e:
            logger.debug(f"❌ Failed to get element attribute: {e}")
            return ""