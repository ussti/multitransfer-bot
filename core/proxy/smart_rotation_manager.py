"""
Smart Proxy Rotation Manager for MultiTransfer.ru
Умный менеджер ротации прокси для снижения капчи с 80% до 10-15%
"""

import logging
import asyncio
import aiohttp
import random
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import threading

logger = logging.getLogger(__name__)

class ProxyQuality(Enum):
    """Качество прокси на основе истории использования"""
    PREMIUM = "premium"      # 0-10% капчи
    GOOD = "good"           # 10-25% капчи  
    AVERAGE = "average"     # 25-50% капчи
    POOR = "poor"          # 50-75% капчи
    BANNED = "banned"      # >75% капчи

class CaptchaType(Enum):
    """Типы капчи для анализа сложности"""
    NONE = "none"
    SIMPLE = "simple"       # Простая капча
    PUZZLE = "puzzle"       # Пазл капча
    COMPLEX = "complex"     # Сложная капча
    RECAPTCHA = "recaptcha" # Google reCAPTCHA

@dataclass
class ProxyStats:
    """Статистика использования прокси"""
    ip: str
    port: str
    user: str
    password: str
    country: str
    
    # Статистика производительности
    total_uses: int = 0
    successful_uses: int = 0
    captcha_encounters: int = 0
    simple_captchas: int = 0
    complex_captchas: int = 0
    
    # Временные метрики
    avg_response_time: float = 0.0
    last_used: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_captcha: Optional[datetime] = None
    
    # Оценки качества
    success_rate: float = 0.0
    captcha_rate: float = 0.0
    quality_score: float = 50.0  # Базовый скор для новых прокси
    quality_level: ProxyQuality = ProxyQuality.AVERAGE
    
    # Экономические метрики
    cost_per_use: float = 0.0
    roi_score: float = 0.0  # Return on Investment
    
    def update_stats(self, success: bool, captcha_type: CaptchaType, response_time: float):
        """Обновить статистику использования"""
        self.total_uses += 1
        self.last_used = datetime.utcnow()
        
        # Обновляем среднее время ответа
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time * 0.8) + (response_time * 0.2)
        
        if success:
            self.successful_uses += 1
            self.last_success = datetime.utcnow()
        
        if captcha_type != CaptchaType.NONE:
            self.captcha_encounters += 1
            self.last_captcha = datetime.utcnow()
            
            if captcha_type in [CaptchaType.SIMPLE]:
                self.simple_captchas += 1
            elif captcha_type in [CaptchaType.PUZZLE, CaptchaType.COMPLEX, CaptchaType.RECAPTCHA]:
                self.complex_captchas += 1
        
        self.recalculate_metrics()
    
    def recalculate_metrics(self):
        """Пересчитать все метрики качества"""
        if self.total_uses > 0:
            self.success_rate = self.successful_uses / self.total_uses
            self.captcha_rate = self.captcha_encounters / self.total_uses
            
            # Вычисляем качественный скор (0-100)
            # Формула: базовый успех - штраф за капчи - штраф за медленность
            base_score = self.success_rate * 100
            captcha_penalty = self.captcha_rate * 50
            speed_penalty = max(0, (self.avg_response_time - 2.0) * 10)
            
            self.quality_score = max(0, base_score - captcha_penalty - speed_penalty)
        else:
            # Новые прокси: устанавливаем базовые значения
            self.success_rate = 0.0
            self.captcha_rate = 0.0
            self.quality_score = 50.0  # Средний стартовый скор
        
        # Определяем уровень качества (реалистичные пороги)
        if self.captcha_rate <= 0.10:
            self.quality_level = ProxyQuality.PREMIUM
        elif self.captcha_rate <= 0.25:
            self.quality_level = ProxyQuality.GOOD
        elif self.captcha_rate <= 0.50:
            self.quality_level = ProxyQuality.AVERAGE
        elif self.captcha_rate <= 0.75:
            self.quality_level = ProxyQuality.POOR
        else:
            self.quality_level = ProxyQuality.BANNED
        
        # ROI Score (учитывает эффективность относительно стоимости)
        if self.cost_per_use > 0:
            self.roi_score = (self.success_rate * 100) / self.cost_per_use
        else:
            self.roi_score = self.success_rate * 100

class SmartProxyRotationManager:
    """Умный менеджер ротации прокси с адаптивным обучением"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.db_path = "data/proxy_analytics.db"
        self.proxy_stats: Dict[str, ProxyStats] = {}
        self.active_proxies: List[ProxyStats] = []
        self.rotation_history: List[Tuple[str, datetime, bool, CaptchaType]] = []
        
        # Настройки алгоритма
        self.max_captcha_rate = 0.15  # Целевая максимальная частота капчи
        self.cooldown_minutes = 30    # Время отдыха после капчи
        self.learning_window = 100    # Окно для анализа трендов
        
        # Стратегии ротации
        self.rotation_strategies = {
            'adaptive': self._adaptive_selection,
            'quality_weighted': self._quality_weighted_selection,
            'anti_pattern': self._anti_pattern_selection,
            'cost_optimized': self._cost_optimized_selection
        }
        
        self.current_strategy = 'adaptive'
        
        # База данных для аналитики
        self._init_database()
        self._load_historical_data()
        
        logger.info("🧠 SmartProxyRotationManager initialized")
    
    def _init_database(self):
        """Инициализация базы данных аналитики"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proxy_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_key TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    success BOOLEAN NOT NULL,
                    captcha_type TEXT NOT NULL,
                    response_time REAL NOT NULL,
                    session_duration REAL,
                    user_agent TEXT,
                    target_country TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proxy_quality_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_key TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    quality_score REAL NOT NULL,
                    captcha_rate REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    total_uses INTEGER NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proxy_sessions_key_time 
                ON proxy_sessions(proxy_key, timestamp)
            """)
    
    def _load_historical_data(self):
        """Загрузить исторические данные о прокси"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT proxy_key, COUNT(*) as total, 
                           SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                           SUM(CASE WHEN captcha_type != 'none' THEN 1 ELSE 0 END) as captchas,
                           AVG(response_time) as avg_time,
                           MAX(timestamp) as last_used
                    FROM proxy_sessions 
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY proxy_key
                """)
                
                for row in cursor.fetchall():
                    proxy_key, total, successful, captchas, avg_time, last_used = row
                    # Восстанавливаем базовую статистику из истории
                    # Полное восстановление будет при первом использовании
                    logger.debug(f"Loaded historical data for {proxy_key}: {total} uses, {successful} successful")
                    
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
    
    async def get_optimal_proxy(self, context: Dict[str, Any] = None) -> Optional[ProxyStats]:
        """
        Получить оптимальный прокси с учетом контекста
        
        Args:
            context: Контекст запроса (страна получателя, сумма, время дня и т.д.)
            
        Returns:
            Оптимальный прокси или None
        """
        if not self.active_proxies:
            logger.warning("No active proxies available")
            return None
        
        context = context or {}
        
        # Определяем стратегию на основе текущей производительности
        current_captcha_rate = self._calculate_recent_captcha_rate()
        
        if current_captcha_rate > self.max_captcha_rate:
            # Переключаемся в агрессивный режим
            strategy = 'anti_pattern'
            logger.info(f"🔥 High captcha rate ({current_captcha_rate:.1%}), using anti-pattern strategy")
        else:
            strategy = self.current_strategy
        
        # Выбираem прокси согласно стратегии
        proxy = await self.rotation_strategies[strategy](context)
        
        if proxy:
            logger.info(f"🎯 Selected proxy {proxy.ip}:{proxy.port} "
                       f"(quality: {proxy.quality_level.value}, "
                       f"captcha rate: {proxy.captcha_rate:.1%})")
        
        return proxy
    
    async def _adaptive_selection(self, context: Dict[str, Any]) -> Optional[ProxyStats]:
        """Адаптивная стратегия выбора на основе машинного обучения"""
        available_proxies = self._get_available_proxies()
        
        if not available_proxies:
            return None
        
        # Весовая функция для каждого прокси
        weighted_proxies = []
        
        for proxy in available_proxies:
            # Базовый вес = качественный скор
            weight = proxy.quality_score
            
            # Бонус за премиум качество
            if proxy.quality_level == ProxyQuality.PREMIUM:
                weight *= 2.0
            elif proxy.quality_level == ProxyQuality.GOOD:
                weight *= 1.5
            
            # Штраф за недавнее использование (избегаем паттернов)
            if proxy.last_used:
                minutes_since_use = (datetime.utcnow() - proxy.last_used).total_seconds() / 60
                if minutes_since_use < 10:  # Использовался менее 10 минут назад
                    weight *= 0.3
                elif minutes_since_use < 30:
                    weight *= 0.7
            
            # Бонус за успех в аналогичном контексте
            if context.get('target_country') and proxy.country == context.get('target_country'):
                weight *= 1.3
            
            # Штраф за недавние капчи
            if proxy.last_captcha:
                minutes_since_captcha = (datetime.utcnow() - proxy.last_captcha).total_seconds() / 60
                if minutes_since_captcha < self.cooldown_minutes:
                    weight *= 0.1  # Сильный штраф
            
            weighted_proxies.append((proxy, max(0.1, weight)))
        
        # Выбираем случайно с учетом весов
        total_weight = sum(weight for _, weight in weighted_proxies)
        if total_weight == 0:
            return random.choice(available_proxies)
        
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for proxy, weight in weighted_proxies:
            current_weight += weight
            if current_weight >= random_value:
                return proxy
        
        return weighted_proxies[-1][0]  # Fallback
    
    async def _quality_weighted_selection(self, context: Dict[str, Any]) -> Optional[ProxyStats]:
        """Выбор на основе качественного скора"""
        available_proxies = self._get_available_proxies()
        
        if not available_proxies:
            return None
        
        # Сортируем по качественному скору
        available_proxies.sort(key=lambda p: p.quality_score, reverse=True)
        
        # Выбираem из топ-30% с вероятностным распределением
        top_count = max(1, len(available_proxies) // 3)
        top_proxies = available_proxies[:top_count]
        
        # Взвешенный выбор из топ прокси
        weights = [p.quality_score + 1 for p in top_proxies]  # +1 чтобы избежать нулевых весов
        return random.choices(top_proxies, weights=weights)[0]
    
    async def _anti_pattern_selection(self, context: Dict[str, Any]) -> Optional[ProxyStats]:
        """Анти-паттерн стратегия для обхода обнаружения"""
        available_proxies = self._get_available_proxies()
        
        if not available_proxies:
            return None
        
        # Избегаем недавно использованных прокси
        unused_proxies = [
            p for p in available_proxies 
            if not p.last_used or 
            (datetime.utcnow() - p.last_used).total_seconds() > 1800  # 30 минут
        ]
        
        if unused_proxies:
            # Выбираем из неиспользованных, приоритет премиум качеству
            premium_unused = [p for p in unused_proxies if p.quality_level == ProxyQuality.PREMIUM]
            if premium_unused:
                return random.choice(premium_unused)
            
            good_unused = [p for p in unused_proxies if p.quality_level == ProxyQuality.GOOD]
            if good_unused:
                return random.choice(good_unused)
            
            return random.choice(unused_proxies)
        
        # Если все использовались недавно, выбираем наименее проблемный
        available_proxies.sort(key=lambda p: (p.captcha_rate, p.last_used or datetime.min))
        return available_proxies[0]
    
    async def _cost_optimized_selection(self, context: Dict[str, Any]) -> Optional[ProxyStats]:
        """Выбор оптимизированный по стоимости (ROI)"""
        available_proxies = self._get_available_proxies()
        
        if not available_proxies:
            return None
        
        # Сортируем по ROI скору
        available_proxies.sort(key=lambda p: p.roi_score, reverse=True)
        
        # Фильтруем слишком проблемные прокси
        good_roi_proxies = [
            p for p in available_proxies 
            if p.captcha_rate <= 0.25  # Максимум 25% капчи
        ]
        
        if good_roi_proxies:
            return good_roi_proxies[0]  # Лучший ROI
        
        return available_proxies[0]  # Fallback на лучший доступный
    
    def _get_available_proxies(self) -> List[ProxyStats]:
        """Получить список доступных прокси с fallback для заблокированных"""
        # Сначала пытаемся получить незаблокированные прокси
        available = [
            p for p in self.active_proxies 
            if p.quality_level != ProxyQuality.BANNED
        ]
        
        # Если все прокси заблокированы, используем лучший из заблокированных
        if not available and self.active_proxies:
            logger.warning("🚨 All proxies are banned, using fallback to best available")
            # Сортируем заблокированные по качественному скору и возвращаем лучший
            banned_proxies = [p for p in self.active_proxies if p.quality_level == ProxyQuality.BANNED]
            if banned_proxies:
                best_banned = max(banned_proxies, key=lambda p: p.quality_score)
                logger.info(f"🔄 Fallback: using banned proxy {best_banned.ip}:{best_banned.port} "
                           f"(score: {best_banned.quality_score:.1f}, captcha: {best_banned.captcha_rate:.1%})")
                return [best_banned]
        
        return available
    
    def _calculate_recent_captcha_rate(self, hours: int = 2) -> float:
        """Вычислить частоту капчи за последние N часов"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_sessions = [
            (success, captcha_type) for _, timestamp, success, captcha_type 
            in self.rotation_history 
            if timestamp >= cutoff_time
        ]
        
        if not recent_sessions:
            return 0.0
        
        captcha_count = sum(1 for _, captcha_type in recent_sessions if captcha_type != CaptchaType.NONE)
        return captcha_count / len(recent_sessions)
    
    async def record_session_result(self, proxy: ProxyStats, success: bool, 
                                  captcha_type: CaptchaType = CaptchaType.NONE,
                                  response_time: float = 0.0, 
                                  session_data: Dict[str, Any] = None):
        """
        Записать результат сессии для обучения алгоритма
        
        Args:
            proxy: Использованный прокси
            success: Успешность операции
            captcha_type: Тип капчи (если была)
            response_time: Время ответа
            session_data: Дополнительные данные сессии
        """
        session_data = session_data or {}
        
        # Обновляем статистику прокси
        proxy.update_stats(success, captcha_type, response_time)
        
        # Записываем в историю
        self.rotation_history.append((
            f"{proxy.ip}:{proxy.port}", 
            datetime.utcnow(), 
            success, 
            captcha_type
        ))
        
        # Ограничиваем размер истории
        if len(self.rotation_history) > 1000:
            self.rotation_history = self.rotation_history[-500:]
        
        # Сохраняем в базу данных
        await self._save_session_to_db(proxy, success, captcha_type, response_time, session_data)
        
        # Логируем результат
        captcha_info = f" (captcha: {captcha_type.value})" if captcha_type != CaptchaType.NONE else ""
        status = "✅" if success else "❌"
        
        logger.info(f"{status} Session result for {proxy.ip}:{proxy.port}: "
                   f"success={success}, time={response_time:.2f}s{captcha_info}")
        
        # Проверяем нужно ли адаптировать стратегию
        await self._adapt_strategy()
    
    async def _save_session_to_db(self, proxy: ProxyStats, success: bool, 
                                captcha_type: CaptchaType, response_time: float,
                                session_data: Dict[str, Any]):
        """Сохранить сессию в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO proxy_sessions 
                    (proxy_key, timestamp, success, captcha_type, response_time, 
                     session_duration, user_agent, target_country)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{proxy.ip}:{proxy.port}",
                    datetime.utcnow(),
                    success,
                    captcha_type.value,
                    response_time,
                    session_data.get('session_duration'),
                    session_data.get('user_agent'),
                    session_data.get('target_country')
                ))
                
        except Exception as e:
            logger.error(f"Error saving session to DB: {e}")
    
    async def _adapt_strategy(self):
        """Адаптировать стратегию на основе результатов"""
        recent_rate = self._calculate_recent_captcha_rate()
        
        # Если капчи слишком много, переключаемся на анти-паттерн
        if recent_rate > 0.25 and self.current_strategy != 'anti_pattern':
            self.current_strategy = 'anti_pattern'
            logger.warning(f"🔄 Switching to anti-pattern strategy due to high captcha rate: {recent_rate:.1%}")
        
        # Если все хорошо, возвращаемся к адаптивной
        elif recent_rate < 0.10 and self.current_strategy == 'anti_pattern':
            self.current_strategy = 'adaptive'
            logger.info(f"🔄 Switching back to adaptive strategy, captcha rate improved: {recent_rate:.1%}")
    
    async def load_proxies_from_provider(self, provider_proxies: List[Dict[str, Any]]):
        """Загрузить прокси от провайдера и создать статистику"""
        self.active_proxies.clear()
        
        for proxy_data in provider_proxies:
            proxy_key = f"{proxy_data['ip']}:{proxy_data['port']}"
            
            # Создаем или обновляем статистику прокси
            if proxy_key in self.proxy_stats:
                proxy_stats = self.proxy_stats[proxy_key]
                # Обновляем данные подключения
                proxy_stats.user = proxy_data.get('user', '')
                proxy_stats.password = proxy_data.get('pass', '')
            else:
                proxy_stats = ProxyStats(
                    ip=proxy_data['ip'],
                    port=proxy_data['port'],
                    user=proxy_data.get('user', ''),
                    password=proxy_data.get('pass', ''),
                    country=proxy_data.get('country', 'ru'),
                    cost_per_use=0.01  # Примерная стоимость за использование
                )
                self.proxy_stats[proxy_key] = proxy_stats
            
            self.active_proxies.append(proxy_stats)
        
        logger.info(f"📊 Loaded {len(self.active_proxies)} proxies for smart rotation")
    
    def get_analytics_report(self) -> Dict[str, Any]:
        """Получить детальный аналитический отчет"""
        if not self.active_proxies:
            return {"error": "No proxies loaded"}
        
        total_proxies = len(self.active_proxies)
        working_proxies = len([p for p in self.active_proxies if p.quality_level != ProxyQuality.BANNED])
        
        quality_distribution = defaultdict(int)
        for proxy in self.active_proxies:
            quality_distribution[proxy.quality_level.value] += 1
        
        avg_captcha_rate = sum(p.captcha_rate for p in self.active_proxies) / total_proxies
        avg_success_rate = sum(p.success_rate for p in self.active_proxies) / total_proxies
        
        recent_captcha_rate = self._calculate_recent_captcha_rate()
        
        return {
            "overview": {
                "total_proxies": total_proxies,
                "working_proxies": working_proxies,
                "current_strategy": self.current_strategy,
                "target_captcha_rate": f"{self.max_captcha_rate:.1%}",
                "actual_recent_captcha_rate": f"{recent_captcha_rate:.1%}",
                "status": "🎯 Target achieved" if recent_captcha_rate <= self.max_captcha_rate else "⚠️ Above target"
            },
            "performance": {
                "avg_captcha_rate": f"{avg_captcha_rate:.1%}",
                "avg_success_rate": f"{avg_success_rate:.1%}",
                "total_sessions": sum(p.total_uses for p in self.active_proxies),
                "successful_sessions": sum(p.successful_uses for p in self.active_proxies)
            },
            "quality_distribution": dict(quality_distribution),
            "top_performers": [
                {
                    "proxy": f"{p.ip}:{p.port}",
                    "quality": p.quality_level.value,
                    "captcha_rate": f"{p.captcha_rate:.1%}",
                    "success_rate": f"{p.success_rate:.1%}",
                    "uses": p.total_uses
                }
                for p in sorted(self.active_proxies, key=lambda x: x.quality_score, reverse=True)[:5]
            ]
        }
    
    async def cleanup_old_data(self, days: int = 30):
        """Очистить старые данные из базы"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM proxy_sessions 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days))
                
                conn.execute("""
                    DELETE FROM proxy_quality_snapshots 
                    WHERE timestamp < datetime('now', '-{} days')
                """.format(days))
                
            logger.info(f"🧹 Cleaned up data older than {days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")


# Интеграция с существующим ProxyManager
class EnhancedProxyManager:
    """Расширенный менеджер прокси с умной ротацией"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        from .manager import ProxyManager
        
        self.base_manager = ProxyManager(config)
        self.smart_rotation = SmartProxyRotationManager(config)
        self.config = config or {}
        
    async def initialize(self):
        """Инициализация обоих менеджеров"""
        await self.base_manager.initialize()
        
        # Загружаем прокси в умную ротацию
        if self.base_manager.proxies:
            await self.smart_rotation.load_proxies_from_provider(self.base_manager.proxies)
    
    async def get_optimal_proxy(self, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Получить оптимальный прокси через умную ротацию"""
        proxy_stats = await self.smart_rotation.get_optimal_proxy(context)
        
        if proxy_stats:
            return {
                'ip': proxy_stats.ip,
                'port': proxy_stats.port,
                'user': proxy_stats.user,
                'pass': proxy_stats.password,
                'country': proxy_stats.country,
                'type': 'http',
                '_stats': proxy_stats  # Внутренняя ссылка для обратной связи
            }
        
        return None
    
    async def record_result(self, proxy: Dict[str, Any], success: bool, 
                          captcha_encountered: bool = False, 
                          captcha_type: str = "none",
                          response_time: float = 0.0):
        """Записать результат использования прокси"""
        if '_stats' in proxy:
            proxy_stats = proxy['_stats']
            captcha_enum = CaptchaType(captcha_type)
            
            await self.smart_rotation.record_session_result(
                proxy_stats, success, captcha_enum, response_time
            )
    
    def get_analytics(self) -> Dict[str, Any]:
        """Получить аналитический отчет"""
        return self.smart_rotation.get_analytics_report()