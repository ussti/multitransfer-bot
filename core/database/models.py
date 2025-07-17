"""
Database models
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, BigInteger, Numeric, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from core.database.connection import Base


class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)  # Telegram user_id
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    requisites = relationship("UserRequisites", back_populates="user", uselist=False)
    payments = relationship("PaymentHistory", back_populates="user")


class UserRequisites(Base):
    """Модель реквизитов пользователя"""
    __tablename__ = 'user_requisites'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, unique=True)
    
    # Данные получателя
    recipient_card = Column(String(20))
    country = Column(String(50))  # tajikistan, georgia, kyrgyzstan
    bank = Column(String(100))    # korti_milli, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="requisites")


class PaymentHistory(Base):
    """Модель истории платежей"""
    __tablename__ = 'payment_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    
    # Детали платежа
    amount = Column(Numeric(10, 2))
    currency_from = Column(String(10))
    currency_to = Column(String(10))
    exchange_rate = Column(Numeric(10, 4))
    
    # Результат
    status = Column(String(50))  # success, failed, pending
    qr_code_url = Column(Text)
    payment_url = Column(Text)
    error_message = Column(Text)
    
    # Техническая информация
    proxy_used = Column(String(100))
    processing_time = Column(Integer)  # секунды
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="payments")


class PassportData(Base):
    """Модель паспортных данных отправителей"""
    __tablename__ = 'passport_data'
    
    id = Column(Integer, primary_key=True)
    
    # Личные данные
    surname = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False) 
    patronymic = Column(String(100), nullable=False)
    birthdate = Column(Date, nullable=False)
    
    # Паспортные данные
    passport_series = Column(String(10), nullable=False)
    passport_number = Column(String(20), nullable=False)
    passport_date = Column(Date, nullable=False)
    passport_country = Column(String(50), default='Россия')
    passport_issued_by = Column(String(200))
    
    # Контактные данные
    phone = Column(String(20), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    
    # Метаданные
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Конвертация в словарь для использования в автоматизации"""
        return {
            'id': self.id,
            'surname': self.surname,
            'name': self.name,
            'patronymic': self.patronymic,
            'birthdate': self.birthdate.strftime('%d.%m.%Y') if self.birthdate else '',
            'passport_series': self.passport_series,
            'passport_number': self.passport_number,
            'passport_date': self.passport_date.strftime('%d.%m.%Y') if self.passport_date else '',
            'passport_country': self.passport_country,
            'passport_issued_by': self.passport_issued_by,
            'phone': self.phone,
            'address': self.address,
            'city': self.city
        }


class PassportStats(Base):
    """Модель статистики использования паспортов"""
    __tablename__ = 'passport_stats'
    
    id = Column(Integer, primary_key=True)
    passport_id = Column(Integer, ForeignKey('passport_data.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Уникальный индекс на комбинацию passport_id + user_id
    __table_args__ = (
        UniqueConstraint('passport_id', 'user_id', name='uq_passport_user'),
    )
    
    # Связи
    passport = relationship("PassportData")
    user = relationship("User")