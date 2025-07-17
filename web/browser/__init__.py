# === web/browser/__init__.py ===
"""
Browser automation components
Contains Chrome browser management and site-specific automation
"""

from .manager import BrowserManager

try:
    from .multitransfer import MultitransferAutomation
    __all__ = ['BrowserManager', 'MultitransferAutomation']
except ImportError:
    # MultitransferAutomation not available yet
    __all__ = ['BrowserManager']