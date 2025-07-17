"""
Database connection configuration
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь к базе данных
DATABASE_URL = f"sqlite+aiosqlite:///{Path(__file__).parent.parent.parent}/data/bot.db"

# Создаем движок
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Логирование SQL запросов
    future=True
)

# Создаем сессию
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для моделей
Base = declarative_base()

def get_async_session() -> AsyncSession:
    """Получить асинхронную сессию"""
    return AsyncSessionLocal()

async def get_async_session_dependency():
    """Получить асинхронную сессию для dependency injection"""
    async with AsyncSessionLocal() as session:
        yield session

async def init_database():
    """Initialize database with all required tables"""
    try:
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
            
            # Создаем таблицу passport_stats отдельно, если нужно
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS passport_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passport_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(passport_id, user_id),
                FOREIGN KEY (passport_id) REFERENCES passport_data(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """)
            
            await conn.commit()
            
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise