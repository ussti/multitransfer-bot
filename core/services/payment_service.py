"""
Payment processing service
Сервис обработки платежей
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from core.database.repositories import UserRepository, PaymentHistoryRepository, PassportDataRepository
from core.database.models import PaymentHistory
from web.browser.multitransfer import MultiTransferAutomation
from core.proxy.manager import ProxyManager
from core.config import get_config
from utils.exceptions import PaymentError, AutomationError
from utils.validators import validate_amount, validate_card_number

logger = logging.getLogger(__name__)

class PaymentService:
    """Сервис для обработки платежей"""
    
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.payment_repo = PaymentHistoryRepository(session)
        self.passport_repo = PassportDataRepository(session)
        self.config = get_config()
        self.proxy_manager = ProxyManager(config=self.config.to_dict())
        
    async def create_payment(
        self, 
        user_id: int, 
        amount: float,
        currency_from: str = "RUB",
        currency_to: str = "TJS"
    ) -> Dict[str, Any]:
        """
        Создание нового платежа
        
        Args:
            user_id: ID пользователя Telegram
            amount: Сумма платежа
            currency_from: Валюта отправителя (по умолчанию RUB)
            currency_to: Валюта получателя (по умолчанию TJS)
            
        Returns:
            Словарь с результатом платежа
        """
        logger.info(f"🔄 Creating payment for user {user_id}: {amount} {currency_from} -> {currency_to}")
        
        start_time = datetime.utcnow()
        payment_record = None
        
        try:
            # Валидация суммы
            if not validate_amount(amount):
                raise PaymentError(f"Invalid amount: {amount}")
            
            # Получаем реквизиты пользователя
            user_requisites = await self.user_repo.get_user_requisites(user_id)
            if not user_requisites:
                raise PaymentError("User requisites not found. Please set up requisites first using /изменить_реквизиты")
            
            # Валидация номера карты
            if not validate_card_number(user_requisites.recipient_card):
                raise PaymentError(f"Invalid card number: {user_requisites.recipient_card}")
            
            # Получаем случайные паспортные данные
            passport_data = await self.passport_repo.get_random_passport()
            if not passport_data:
                raise PaymentError("No passport data available for payment processing")
            
            logger.info(f"🔍 FULL passport data content: {passport_data.to_dict()}")
            
            # Отмечаем использование паспорта
            await self.passport_repo.mark_passport_used(passport_data.id)
            
            # Создаем запись в истории платежей
            payment_record = PaymentHistory(
                user_id=user_id,
                amount=amount,
                currency_from=currency_from,
                currency_to=currency_to,
                status="pending"
            )
            
            payment_record = await self.payment_repo.create_payment(payment_record)
            payment_id = payment_record.id
            
            logger.info(f"💾 Created payment record ID: {payment_id}")
            
            # Получаем прокси
            proxy = await self.proxy_manager.get_proxy()
            if proxy:
                logger.info(f"🌐 Using proxy: {proxy['ip']}:{proxy['port']}")
                payment_record.proxy_used = f"{proxy['ip']}:{proxy['port']}"
            else:
                logger.warning("⚠️ No proxy available, using direct connection")
            
            # Подготавливаем данные для автоматизации
            automation_data = {
                'amount': amount,
                'currency_from': currency_from,
                'currency_to': currency_to,
                'recipient_card': user_requisites.recipient_card,
                'country': user_requisites.country,
                'bank': user_requisites.bank,
                'passport_data': passport_data.to_dict()
            }
            
            logger.info(f"🚀 Starting browser automation...")
            logger.info(f"📄 Automation data: Country={user_requisites.country}, Bank={user_requisites.bank}, Card={user_requisites.recipient_card[:4]}****")
            
            # Запускаем браузерную автоматизацию
            automation = MultiTransferAutomation(proxy=proxy, config=self.config.to_dict())
            result = await automation.create_payment(automation_data)
            
            # Обновляем запись платежа
            processing_time = int((datetime.utcnow() - start_time).total_seconds())
            
            if result.get('success'):
                payment_record.status = "success"
                payment_record.qr_code_url = result.get('qr_code_url')
                payment_record.payment_url = result.get('payment_url')
                payment_record.exchange_rate = result.get('exchange_rate')
                
                logger.info(f"✅ Payment successful: {payment_id}")
                
            else:
                payment_record.status = "failed"
                payment_record.error_message = result.get('error', 'Unknown error')
                
                logger.error(f"❌ Payment failed: {payment_id} - {payment_record.error_message}")
                
                # Отмечаем прокси как проблемный, если ошибка связана с блокировкой
                if proxy and any(word in payment_record.error_message.lower() for word in ['blocked', 'banned', 'timeout', 'connection']):
                    await self.proxy_manager.mark_proxy_failed(proxy['ip'], proxy['port'])
            
            payment_record.processing_time = processing_time
            await self.payment_repo.update_payment(payment_record)
            
            # Формируем ответ
            response = {
                'payment_id': payment_id,
                'status': payment_record.status,
                'amount': amount,
                'currency_from': currency_from,
                'currency_to': currency_to,
                'processing_time': processing_time,
                'passport_used': f"{passport_data.surname} {passport_data.name}"
            }
            
            if payment_record.status == "success":
                response.update({
                    'qr_code_url': payment_record.qr_code_url,
                    'payment_url': payment_record.payment_url,
                    'exchange_rate': payment_record.exchange_rate
                })
            else:
                response['error'] = payment_record.error_message
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Payment service error: {e}")
            
            # Обновляем статус платежа при ошибке
            try:
                if payment_record:
                    payment_record.status = "failed"
                    payment_record.error_message = str(e)
                    payment_record.processing_time = int((datetime.utcnow() - start_time).total_seconds())
                    await self.payment_repo.update_payment(payment_record)
            except Exception as update_error:
                logger.error(f"Failed to update payment record: {update_error}")
            
            raise PaymentError(f"Payment processing failed: {str(e)}")
    
    async def get_payment_status(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Получить статус платежа по ID"""
        logger.info(f"📊 Getting payment status: {payment_id}")
        
        payment = await self.payment_repo.get_payment_by_id(payment_id)
        if not payment:
            return None
        
        return {
            'payment_id': payment.id,
            'status': payment.status,
            'amount': float(payment.amount) if payment.amount else 0,
            'currency_from': payment.currency_from,
            'currency_to': payment.currency_to,
            'qr_code_url': payment.qr_code_url,
            'payment_url': payment.payment_url,
            'error_message': payment.error_message,
            'processing_time': payment.processing_time,
            'created_at': payment.created_at.isoformat() if payment.created_at else None
        }
    
    async def get_user_payment_history(self, user_id: int, limit: int = 10) -> list:
        """Получить историю платежей пользователя"""
        logger.info(f"📜 Getting payment history for user {user_id}")
        
        payments = await self.payment_repo.get_user_payments(user_id, limit)
        
        return [
            {
                'payment_id': payment.id,
                'amount': float(payment.amount) if payment.amount else 0,
                'status': payment.status,
                'currency_from': payment.currency_from,
                'currency_to': payment.currency_to,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'processing_time': payment.processing_time
            }
            for payment in payments
        ]