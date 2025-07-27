#!/usr/bin/env python3
"""
Load passport data from Excel file to database
Загрузка паспортных данных из Excel файла в базу данных
"""

import asyncio
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database.connection import AsyncSessionLocal, engine
from core.database.models import Base, PassportData
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def load_passport_data():
    """Загрузка паспортных данных из Excel"""
    logger.info("🔄 Loading passport data from Excel...")
    
    try:
        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created/verified")
        
        # Читаем Excel файл
        excel_file = Path(__file__).parent / "люди паспорта.xlsx"
        if not excel_file.exists():
            logger.error(f"❌ Excel file not found: {excel_file}")
            return
        
        logger.info(f"📊 Reading Excel file: {excel_file}")
        df = pd.read_excel(excel_file, header=None)
        
        logger.info(f"📋 Found {len(df)} records in Excel")
        
        # Создаем сессию
        async with AsyncSessionLocal() as session:
            # Проверяем, есть ли уже данные
            from sqlalchemy import select, func
            result = await session.execute(select(func.count(PassportData.id)))
            existing_count = result.scalar()
            
            if existing_count > 0:
                logger.info(f"ℹ️ Found {existing_count} existing passport records")
                response = input("🤔 Clear existing data and reload? (y/N): ")
                if response.lower() != 'y':
                    logger.info("❌ Cancelled by user")
                    return
                
                # Удаляем существующие данные
                from sqlalchemy import text
                await session.execute(text("DELETE FROM passport_data"))
                await session.commit()
                logger.info("🗑️ Cleared existing data")
            
            logger.info("📝 Loading passport records...")
            
            loaded_count = 0
            for index, row in df.iterrows():
                try:
                    # Парсим данные из строки
                    full_name = str(row[0]).strip()
                    name_parts = full_name.split()
                    
                    if len(name_parts) < 3:
                        logger.warning(f"⚠️ Invalid name format in row {index}: {full_name}")
                        continue
                    
                    surname = name_parts[0]
                    name = name_parts[1] 
                    patronymic = name_parts[2]
                    
                    # Парсим дату рождения
                    birth_date = pd.to_datetime(row[1]).date()
                    
                    # Паспортные данные
                    passport_series = str(row[2]).strip()
                    passport_number = str(row[3]).strip()
                    passport_date = pd.to_datetime(row[4]).date()
                    
                    # Дополнительные данные
                    subdivision_code = str(row[5]).strip() if pd.notna(row[5]) else ""
                    issued_by = str(row[6]).strip() if pd.notna(row[6]) else ""
                    address = str(row[7]).strip() if pd.notna(row[7]) else ""
                    snils = str(row[8]).strip() if pd.notna(row[8]) else ""
                    birth_place = str(row[9]).strip() if pd.notna(row[9]) else ""
                    
                    # Генерируем номер телефона (базовый)
                    phone = f"+7{9000000000 + index}"
                    
                    # Извлекаем город из адреса
                    city = "Новосибирск"  # По умолчанию
                    if "г," in address:
                        city_part = address.split("г,")[1].split(",")[0].strip()
                        if city_part:
                            city = city_part
                    
                    # Создаем запись
                    passport_record = PassportData(
                        surname=surname,
                        name=name,
                        patronymic=patronymic,
                        birthdate=birth_date,
                        passport_series=passport_series,
                        passport_number=passport_number,
                        passport_date=passport_date,
                        passport_country='Россия',
                        passport_issued_by=issued_by,
                        phone=phone,
                        address=address,
                        city=city
                    )
                    
                    session.add(passport_record)
                    loaded_count += 1
                    
                    # Коммитим по батчам
                    if loaded_count % 100 == 0:
                        await session.commit()
                        logger.info(f"💾 Loaded {loaded_count} records...")
                
                except Exception as e:
                    logger.warning(f"⚠️ Error processing row {index}: {e}")
                    continue
            
            # Финальный коммит
            await session.commit()
            logger.info(f"✅ Successfully loaded {loaded_count} passport records")
            
            # Показываем статистику
            result = await session.execute(select(func.count(PassportData.id)))
            total_count = result.scalar()
            logger.info(f"📊 Total records in database: {total_count}")
        
        logger.info("🎯 Passport data loading completed")
        
    except Exception as e:
        logger.error(f"❌ Error during loading: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(load_passport_data())
