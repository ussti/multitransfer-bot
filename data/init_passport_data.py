#!/usr/bin/env python3
"""
Initialize passport data in database
Инициализация паспортных данных в базе данных
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database.connection import get_async_session
from core.database.repositories import PassportDataRepository
from core.database.models import Base, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_passport_data():
    """Инициализация паспортных данных"""
    logger.info("🔄 Initializing passport data...")
    
    # Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Добавляем тестовые данные
    async with get_async_session() as session:
        passport_repo = PassportDataRepository(session)
        
        # Проверяем, есть ли уже данные
        existing_passports = await passport_repo.get_all_passports()
        
        if not existing_passports:
            logger.info("📝 Creating sample passport data...")
            await passport_repo.create_sample_data()
            logger.info("✅ Sample passport data created")
        else:
            logger.info(f"ℹ️ Found {len(existing_passports)} existing passport records")
    
    logger.info("🎯 Passport data initialization completed")

if __name__ == "__main__":
    asyncio.run(init_passport_data())
