"""
Database repositories for MultiTransfer Bot
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError

from .models import User, UserRequisites, PaymentHistory, PassportData

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_user(
        self, 
        user_id: int, 
        username: str = None, 
        first_name: str = None,
        last_name: str = None,
        language_code: str = None
    ) -> User:
        """Get existing user or create new one"""
        try:
            # Ищем существующего пользователя
            result = await self.session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Обновляем информацию если что-то изменилось
                if username and user.username != username:
                    user.username = username
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                if language_code and user.language_code != language_code:
                    user.language_code = language_code
                
                user.updated_at = datetime.utcnow()
                await self.session.commit()
                logger.info(f"📝 User {user_id} updated")
            else:
                # Создаем нового пользователя
                user = User(
                    id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code
                )
                self.session.add(user)
                await self.session.commit()
                await self.session.refresh(user)
                logger.info(f"✅ User {user_id} created")
            
            return user
            
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            await self.session.rollback()
            raise
    
    async def get_user_requisites(self, user_id: int) -> Optional[UserRequisites]:
        """Get user requisites"""
        try:
            result = await self.session.execute(
                select(UserRequisites).where(UserRequisites.user_id == user_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting user requisites: {e}")
            return None


class UserRequisitesRepository:
    """Repository for UserRequisites operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_requisites(self, user_id: int) -> Optional[UserRequisites]:
        """Get user requisites by user_id"""
        try:
            result = await self.session.execute(
                select(UserRequisites).where(UserRequisites.user_id == user_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error in get_user_requisites: {e}")
            return None
    
    async def upsert_requisites(
        self, 
        user_id: int, 
        recipient_card: str, 
        country: str, 
        bank: str
    ) -> bool:
        """Create or update user requisites"""
        try:
            # Ищем существующие реквизиты
            result = await self.session.execute(
                select(UserRequisites).where(UserRequisites.user_id == user_id)
            )
            requisites = result.scalar_one_or_none()
            
            if requisites:
                # Обновляем существующие
                requisites.recipient_card = recipient_card
                requisites.country = country
                requisites.bank = bank
                requisites.updated_at = datetime.utcnow()
                logger.info(f"📝 Requisites updated for user {user_id}")
            else:
                # Создаем новые
                requisites = UserRequisites(
                    user_id=user_id,
                    recipient_card=recipient_card,
                    country=country,
                    bank=bank
                )
                self.session.add(requisites)
                logger.info(f"✅ Requisites created for user {user_id}")
            
            await self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error in upsert_requisites: {e}")
            await self.session.rollback()
            return False
    
    async def delete_user_requisites(self, user_id: int) -> bool:
        """Delete user requisites"""
        try:
            await self.session.execute(
                delete(UserRequisites).where(UserRequisites.user_id == user_id)
            )
            await self.session.commit()
            logger.info(f"🗑️ Requisites deleted for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in delete_user_requisites: {e}")
            await self.session.rollback()
            return False


class PaymentHistoryRepository:
    """Repository for payment history operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_payment(self, payment: PaymentHistory) -> PaymentHistory:
        """Create new payment record"""
        try:
            self.session.add(payment)
            await self.session.commit()
            await self.session.refresh(payment)
            logger.info(f"✅ Payment record {payment.id} created")
            return payment
            
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            await self.session.rollback()
            raise
    
    async def update_payment(self, payment: PaymentHistory) -> PaymentHistory:
        """Update existing payment record"""
        try:
            await self.session.commit()
            logger.info(f"📝 Payment record {payment.id} updated")
            return payment
            
        except Exception as e:
            logger.error(f"Error updating payment: {e}")
            await self.session.rollback()
            raise
    
    async def get_payment_by_id(self, payment_id: int) -> Optional[PaymentHistory]:
        """Get payment by ID"""
        try:
            result = await self.session.execute(
                select(PaymentHistory).where(PaymentHistory.id == payment_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting payment by ID: {e}")
            return None
    
    async def get_user_payments(self, user_id: int, limit: int = 10) -> List[PaymentHistory]:
        """Get user payment history"""
        try:
            result = await self.session.execute(
                select(PaymentHistory)
                .where(PaymentHistory.user_id == user_id)
                .order_by(PaymentHistory.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting user payments: {e}")
            return []


class PassportDataRepository:
    """Репозиторий для работы с паспортными данными - УЛУЧШЕННАЯ ЛОГИКА"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_random_passport_data(self, user_id: int = None) -> Optional[Dict]:
        """
        Get passport data with smart rotation logic:
        - Use same person until errors occur
        - Track success/failure per person
        - Rotate only when needed
        """
        try:
            # Get current "preferred" passport for this user
            current_query = """
            SELECT 
                p.*,
                COALESCE(ps.success_count, 0) as success_count,
                COALESCE(ps.error_count, 0) as error_count,
                COALESCE(ps.last_used, '1970-01-01') as last_used
            FROM passport_data p
            LEFT JOIN passport_stats ps ON p.id = ps.passport_id AND ps.user_id = ?
            WHERE p.is_active = 1
            ORDER BY 
                ps.last_used ASC NULLS FIRST,  -- Prefer least recently used
                ps.error_count ASC NULLS FIRST, -- Prefer those with fewer errors
                RANDOM()
            LIMIT 1
            """
            
            result = await self.session.execute(current_query, (user_id,))
            current = result.fetchone()
            
            if current:
                # Check if current passport is still good to use
                success_count = current.success_count or 0
                error_count = current.error_count or 0
                
                # Use same person if:
                # - Less than 5 successful operations OR
                # - Success rate > 80% and less than 10 total operations
                total_ops = success_count + error_count
                success_rate = success_count / max(total_ops, 1)
                
                should_continue = (
                    total_ops < 5 or  # First few operations
                    (success_rate > 0.8 and total_ops < 10)  # Good success rate
                )
                
                if should_continue:
                    logger.info(f"📋 Continuing with passport: {current.surname} {current.name} "
                              f"(success: {success_count}, errors: {error_count})")
                    return current._asdict() if hasattr(current, '_asdict') else dict(current)
            
            # Need new passport - get least used one
            new_query = """
            SELECT 
                p.*,
                COALESCE(ps.success_count, 0) as success_count,
                COALESCE(ps.error_count, 0) as error_count,
                COALESCE(ps.last_used, '1970-01-01') as last_used
            FROM passport_data p
            LEFT JOIN passport_stats ps ON p.id = ps.passport_id
            WHERE p.is_active = 1 AND p.id NOT IN (
                SELECT passport_id FROM passport_stats 
                WHERE error_count > 3  -- Exclude frequently failing passports
            )
            ORDER BY 
                COALESCE(ps.success_count + ps.error_count, 0) ASC,  -- Prefer unused
                ps.last_used ASC NULLS FIRST,
                RANDOM()
            LIMIT 1
            """
            
            result = await self.session.execute(new_query)
            passport = result.fetchone()
            
            if passport:
                logger.info(f"📋 Selected NEW passport: {passport.surname} {passport.name} "
                          f"(used {getattr(passport, 'success_count', 0)} times)")
                return passport._asdict() if hasattr(passport, '_asdict') else dict(passport)
            
            logger.error("❌ No suitable passport data found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting passport data: {e}")
            return None

    async def update_passport_usage(self, passport_id: int, user_id: int, success: bool):
        """Update passport usage statistics"""
        try:
            # Insert or update stats
            query = """
            INSERT INTO passport_stats (passport_id, user_id, success_count, error_count, last_used)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(passport_id, user_id) DO UPDATE SET
                success_count = success_count + CASE WHEN ? THEN 1 ELSE 0 END,
                error_count = error_count + CASE WHEN ? THEN 0 ELSE 1 END,
                last_used = datetime('now')
            """
            
            await self.session.execute(query, (
                passport_id, user_id, 
                1 if success else 0, 
                0 if success else 1,
                success, success
            ))
            await self.session.commit()
            
            status = "✅ SUCCESS" if success else "❌ ERROR"
            logger.info(f"📊 Passport {passport_id} usage updated: {status}")
            
        except Exception as e:
            logger.error(f"❌ Error updating passport usage: {e}")

    async def get_random_passport(self) -> Optional[PassportData]:
        """Получить случайные активные паспортные данные (старый метод для совместимости)"""
        try:
            # Получаем активную запись с минимальным использованием
            result = await self.session.execute(
                select(PassportData)
                .where(PassportData.is_active == True)
                .order_by(PassportData.usage_count.asc(), func.random())
                .limit(1)
            )
            passport = result.scalar_one_or_none()
            
            if not passport:
                logger.warning("⚠️ No active passport data found")
                return None
            
            logger.info(f"📋 Selected passport: {passport.surname} {passport.name} (used {passport.usage_count} times)")
            return passport
            
        except Exception as e:
            logger.error(f"Error getting random passport: {e}")
            return None
    
    async def mark_passport_used(self, passport_id: int) -> bool:
        """Отметить паспорт как использованный (старый метод для совместимости)"""
        try:
            await self.session.execute(
                update(PassportData)
                .where(PassportData.id == passport_id)
                .values(
                    usage_count=PassportData.usage_count + 1,
                    last_used=datetime.utcnow()
                )
            )
            await self.session.commit()
            logger.info(f"📊 Passport {passport_id} usage count updated")
            return True
            
        except Exception as e:
            logger.error(f"Error marking passport as used: {e}")
            await self.session.rollback()
            return False
    
    async def get_all_passports(self) -> List[PassportData]:
        """Получить все паспортные данные"""
        try:
            result = await self.session.execute(select(PassportData))
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting all passports: {e}")
            return []
    
    async def create_passport(self, passport_data: dict) -> Optional[PassportData]:
        """Создать новую запись паспортных данных"""
        try:
            passport = PassportData(**passport_data)
            self.session.add(passport)
            await self.session.commit()
            await self.session.refresh(passport)
            return passport
            
        except Exception as e:
            logger.error(f"Error creating passport: {e}")
            await self.session.rollback()
            return None
    
    async def create_sample_data(self):
        """Создать тестовые данные"""
        sample_passports = [
            {
                'surname': 'Иванов',
                'name': 'Иван',
                'patronymic': 'Иванович',
                'birthdate': datetime(1990, 1, 1).date(),
                'passport_series': '1234',
                'passport_number': '567890',
                'passport_date': datetime(2020, 1, 1).date(),
                'passport_country': 'Россия',
                'passport_issued_by': 'ОТДЕЛОМ УФМС РОССИИ ПО Г. МОСКВА',
                'phone': '+79123456789',
                'address': 'ул. Тестовая, д. 1, кв. 1',
                'city': 'Москва'
            },
            {
                'surname': 'Петров',
                'name': 'Петр', 
                'patronymic': 'Петрович',
                'birthdate': datetime(1985, 5, 15).date(),
                'passport_series': '4567',
                'passport_number': '123456',
                'passport_date': datetime(2015, 5, 15).date(),
                'passport_country': 'Россия',
                'passport_issued_by': 'ОТДЕЛОМ УФМС РОССИИ ПО Г. САНКТ-ПЕТЕРБУРГ',
                'phone': '+79876543210',
                'address': 'ул. Невский проспект, д. 50, кв. 25',
                'city': 'Санкт-Петербург'
            },
            {
                'surname': 'Сидорова',
                'name': 'Анна',
                'patronymic': 'Алексеевна',
                'birthdate': datetime(1992, 8, 10).date(),
                'passport_series': '7890',
                'passport_number': '654321',
                'passport_date': datetime(2022, 8, 10).date(),
                'passport_country': 'Россия',
                'passport_issued_by': 'ОТДЕЛОМ УФМС РОССИИ ПО Г. НОВОСИБИРСК',
                'phone': '+79555123456',
                'address': 'ул. Ленина, д. 25, кв. 10',
                'city': 'Новосибирск'
            }
        ]
        
        for passport_data in sample_passports:
            await self.create_passport(passport_data)
        
        logger.info(f"✅ Created {len(sample_passports)} sample passport records")