# === core/services/__init__.py ===
"""
Business logic services for MultiTransfer Bot
Contains payment processing and other core services
"""

try:
    from .payment_service import PaymentService
    __all__ = ['PaymentService']
except ImportError:
    # PaymentService not available yet
    __all__ = []