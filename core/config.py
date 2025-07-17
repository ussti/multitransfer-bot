"""
Configuration Management for MultiTransfer Bot
Loads settings from config.yml and environment variables
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager"""
    
    def __init__(self):
        self.data = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file and environment"""
        try:
            # Load environment variables from .env file
            load_dotenv()
            
            # Принудительная установка API ключа для captcha
            if not os.getenv('CAPTCHA_API_KEY'):
                os.environ['CAPTCHA_API_KEY'] = '0b08f459ac08cfbc80134acc46d7ed1f'
                logger.warning("⚠️ CAPTCHA_API_KEY set manually for debugging")
            
            # Load config.yml
            config_path = Path("config.yml")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.data = yaml.safe_load(f)
                logger.info("✅ Configuration loaded from config.yml")
            else:
                logger.warning("⚠️ config.yml not found, using defaults")
                self.data = self._get_default_config()
            
            # Replace environment variables
            self._replace_env_vars(self.data)
            
            # Validate required settings
            self._validate_config()
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
    
    def _replace_env_vars(self, obj):
        """Recursively replace ${VAR} with environment variables"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = self._replace_env_vars(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                obj[i] = self._replace_env_vars(item)
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            default_value = None
            
            # Handle default values like ${VAR:-default}
            if ":-" in env_var:
                env_var, default_value = env_var.split(":-", 1)
            
            # Get environment variable value
            env_value = os.getenv(env_var, default_value)
            
            # Convert string values to appropriate types
            if env_value is not None:
                # Convert boolean strings
                if env_value.lower() in ('true', 'false'):
                    return env_value.lower() == 'true'
                # Convert numeric strings
                elif env_value.isdigit():
                    return int(env_value)
                # Return as string
                else:
                    return env_value
            
            return env_value
        
        return obj
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "telegram": {
                "token": os.getenv("BOT_TOKEN"),
                "webhook_url": os.getenv("BOT_WEBHOOK_URL"),
                "allowed_updates": ["message", "callback_query"],
                "parse_mode": "HTML"
            },
            "database": {
                "url": os.getenv("DATABASE_URL", "sqlite:///data/bot.db"),
                "echo": False,
                "pool_size": 5,
                "max_overflow": 10
            },
            "proxy": {
                "provider": os.getenv("PROXY_PROVIDER", "proxy6"),
                "api_key": os.getenv("PROXY_API_KEY"),
                "country": os.getenv("PROXY_COUNTRY", "ru"),
                "rotation_enabled": os.getenv("PROXY_ROTATION_ENABLED", "true").lower() == "true",
                "max_failures_per_proxy": int(os.getenv("PROXY_MAX_FAILURES", "3")),
                "check_interval": 300
            },
            "captcha": {
                "provider": os.getenv("CAPTCHA_PROVIDER", "anticaptcha"),
                "api_key": os.getenv("CAPTCHA_API_KEY"),
                "timeout": int(os.getenv("CAPTCHA_TIMEOUT", "120")),
                "max_attempts": int(os.getenv("CAPTCHA_MAX_ATTEMPTS", "3")),
                "plugin_enabled": True,
                "plugin_path": "plugins",
                "enabled": True
            },
            "multitransfer": {
                "base_url": os.getenv("MULTITRANSFER_BASE_URL", "https://multitransfer.ru"),
                "supported_countries": {
                    "tajikistan": {
                        "name": "Таджикистан",
                        "currency": "TJS",
                        "banks": ["korti_milli", "azizi_molia", "bank_arvand", "eskhata_bank"]
                    },
                    "georgia": {
                        "name": "Грузия", 
                        "currency": "GEL",
                        "banks": ["bog_bank", "tbc_bank"]
                    },
                    "kyrgyzstan": {
                        "name": "Киргизия",
                        "currency": "KGS", 
                        "banks": ["optima_bank", "demir_bank"]
                    }
                },
                "supported_currencies": ["RUB", "USD", "EUR", "TJS", "KGS", "GEL"],
                "min_amount": int(os.getenv("MULTITRANSFER_MIN_AMOUNT", "300")),
                "max_amount": int(os.getenv("MULTITRANSFER_MAX_AMOUNT", "120000")),
                "timeout": int(os.getenv("MULTITRANSFER_TIMEOUT", "30"))
            },
            "browser": {
                "headless": os.getenv("BROWSER_HEADLESS", "true").lower() == "true",
                "window_size": os.getenv("BROWSER_WINDOW_SIZE", "1920,1080"),
                "page_load_timeout": int(os.getenv("BROWSER_PAGE_LOAD_TIMEOUT", "30")),
                "implicit_wait": int(os.getenv("BROWSER_IMPLICIT_WAIT", "10")),
                "user_agents": [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            },
            "logging": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": os.getenv("LOG_FILE", "logs/bot.log"),
                "max_file_size": os.getenv("LOG_MAX_FILE_SIZE", "10MB"),
                "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5"))
            },
            "railway": {
                "port": int(os.getenv("PORT", "8000")),
                "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
            },
            "development": {
                "debug": os.getenv("DEBUG", "false").lower() == "true",
                "development_mode": os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
            }
        }
    
    def _validate_config(self):
        """Validate required configuration"""
        required_fields = [
            ("telegram.token", "Telegram bot token is required"),
            ("proxy.api_key", "Proxy6.net API key is required for production")
        ]
        
        errors = []
        
        for field_path, error_msg in required_fields:
            value = self.get(field_path)
            if not value:
                # Allow missing proxy API key in development mode
                if field_path == "proxy.api_key" and self.is_development():
                    continue
                errors.append(error_msg)
        
        if errors:
            logger.error("❌ Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Configuration validation failed")
        
        logger.info("✅ Configuration validation passed")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot notation path"""
        keys = key_path.split('.')
        value = self.data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """Set configuration value by dot notation path"""
        keys = key_path.split('.')
        target = self.data
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        target[keys[-1]] = value
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.get("development.development_mode", False) or self.get("development.debug", False)
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            self._validate_config()
            return True
        except ValueError:
            return False
    
    @property
    def telegram(self) -> Dict[str, Any]:
        """Get telegram configuration"""
        return self.data.get("telegram", {})
    
    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.data.get("database", {})
    
    @property
    def proxy(self) -> Dict[str, Any]:
        """Get proxy configuration"""
        return self.data.get("proxy", {})
    
    @property
    def captcha(self) -> Dict[str, Any]:
        """Get captcha configuration"""
        return self.data.get("captcha", {})
    
    @property
    def multitransfer(self) -> Dict[str, Any]:
        """Get multitransfer configuration"""
        return self.data.get("multitransfer", {})
    
    @property
    def browser(self) -> Dict[str, Any]:
        """Get browser configuration"""
        return self.data.get("browser", {})
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.data.get("logging", {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary"""
        return self.data.copy()


# Global configuration instance
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def load_config() -> Dict[str, Any]:
    """Load configuration and return as dictionary (for compatibility)"""
    config = get_config()
    return config.to_dict()

def reload_config():
    """Reload configuration"""
    global _config_instance
    _config_instance = Config()
    return _config_instance