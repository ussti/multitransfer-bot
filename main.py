"""
MultiTransfer Telegram Bot
Main application entry point
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Core imports
from core.config import get_config
from core.database.connection import AsyncSessionLocal, engine, Base
from core.database.repositories import UserRepository, UserRequisitesRepository, PaymentHistoryRepository
from core.services.payment_service import PaymentService
from utils.validators import validate_card_number
from utils.exceptions import PaymentError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log')
    ]
)

logger = logging.getLogger(__name__)

# FSM States
class RequisitesStates(StatesGroup):
    waiting_for_card = State()

# Global variables
config = None
storage = MemoryStorage()
bot = None
dp = Dispatcher(storage=storage)

def format_card_number(card_number: str) -> str:
    """Format card number with spaces"""
    clean = card_number.replace(' ', '').replace('-', '')
    return ' '.join([clean[i:i+4] for i in range(0, len(clean), 4)])

async def init_database():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

def get_countries_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for country selection"""
    buttons = [
        [InlineKeyboardButton(text="🇹🇯 Таджикистан", callback_data="country_tajikistan")],
        [InlineKeyboardButton(text="🇬🇪 Грузия", callback_data="country_georgia")],
        [InlineKeyboardButton(text="🇰🇬 Киргизия", callback_data="country_kyrgyzstan")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_banks_keyboard(country: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for bank selection based on country"""
    banks_data = {
        'tajikistan': [
            ('🏦 Корти Милли', 'bank_korti_milli'),
            ('🏦 Азизи-Молия', 'bank_azizi_molia'),
            ('🏦 Банк Арванд', 'bank_bank_arvand'),
            ('🏦 Эсхата Банк', 'bank_eskhata_bank')
        ],
        'georgia': [
            ('🏦 Bank of Georgia', 'bank_bog_bank'),
            ('🏦 TBC Bank', 'bank_tbc_bank')
        ],
        'kyrgyzstan': [
            ('🏦 Оптима Банк', 'bank_optima_bank'),
            ('🏦 Демир Банк', 'bank_demir_bank')
        ]
    }
    
    buttons = []
    for bank_name, bank_code in banks_data.get(country, []):
        buttons.append([InlineKeyboardButton(text=bank_name, callback_data=bank_code)])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к выбору страны", callback_data="back_to_countries")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Handler for /start command"""
    user_name = message.from_user.full_name if message.from_user else "Пользователь"
    
    welcome_text = f"""
🤖 <b>Добро пожаловать в MultiTransfer Bot!</b>

Привет, {user_name}! 👋

Я помогу вам создавать платежи через multitransfer.ru автоматически.

<b>📋 Доступные команды:</b>
/start - показать это сообщение
/help - справка по использованию  
/settings - настройка ваших реквизитов
/payment [сумма] - создать новый платеж
/proxy - статус прокси-серверов

<b>🚀 Начнем?</b>
Сначала настройте ваши реквизиты командой /settings
    """
    
    await message.answer(welcome_text)
    logger.info(f"User {message.from_user.id} started the bot")

@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """Handler for /help command"""
    help_text = """
<b>🔧 Справка по использованию бота</b>

<b>Основные команды:</b>
• <code>/start</code> - главное меню
• <code>/help</code> - эта справка
• <code>/settings</code> - настройка реквизитов
• <code>/payment [сумма]</code> - создать платеж
• <code>/proxy</code> - статус прокси-серверов

<b>Примеры использования:</b>
• <code>/payment 5000</code> - платеж на 5000 рублей
• <code>/payment 1500</code> - платеж на 1500 рублей

<b>📝 Перед первым платежом:</b>
1. Выполните <code>/settings</code>
2. Укажите страну назначения
3. Выберите банк получателя
4. Введите номер карты получателя
5. Готово! Теперь можно создавать платежи

<b>⚡ Автоматизация:</b>
Бот автоматически заполнит все формы на сайте multitransfer.ru и вернет вам QR-код для оплаты.

<b>🔒 Безопасность:</b>
Все ваши данные хранятся локально и защищены.
    """
    await message.answer(help_text)

@dp.message(Command("proxy"))
async def command_proxy_handler(message: Message) -> None:
    """Handler for /proxy command"""
    try:
        logger.info(f"Proxy status command received from user {message.from_user.id}")
        
        # Создаем ProxyManager для получения статистики
        from core.proxy.manager import ProxyManager
        config_dict = config.to_dict()
        proxy_manager = ProxyManager(config_dict)
        
        # Получаем статистику
        stats = proxy_manager.get_stats()
        
        # Пытаемся получить прокси для теста
        try:
            proxy = await proxy_manager.get_proxy()
            proxy_info = ""
            if proxy:
                proxy_info = f"""
🌐 <b>Активный прокси:</b>
• IP: <code>{proxy['ip']}:{proxy['port']}</code>
• Страна: {proxy.get('country', 'N/A')}
• Пользователь: <code>{proxy.get('user', 'N/A')}</code>
"""
            else:
                proxy_info = "\n⚠️ <b>Прокси недоступны</b> - работаем в прямом режиме"
        except Exception as e:
            proxy_info = f"\n❌ <b>Ошибка получения прокси:</b> {str(e)}"
        
        # Формируем ответ
        proxy_text = f"""
🌐 <b>Статус прокси-серверов</b>

📊 <b>Статистика:</b>
• Всего прокси: {stats['total_proxies']}
• Рабочих: {stats['working_proxies']}
• Сломанных: {stats['failed_proxies']}
• Успешность: {stats['success_rate']}
• Режим: {'🌐 Прокси' if stats['enabled'] else '🔒 Прямое соединение'}
• API ключ: {'✅ Настроен' if stats['api_key_configured'] else '❌ Не настроен'}
• Обновление: {stats['last_update'] or 'Никогда'}
{proxy_info}

💡 <b>Подсказка:</b> Если прокси недоступны, проверьте баланс на Proxy6.net и купите активные прокси.
"""
        
        await message.answer(proxy_text)
        
    except Exception as e:
        logger.error(f"Error in proxy command: {e}")
        await message.answer(
            "❌ <b>Ошибка получения статистики прокси</b>\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )

@dp.message(Command("settings"))
async def command_settings_handler(message: Message, state: FSMContext) -> None:
    """Handler for /settings command"""
    logger.info(f"Settings command received from user {message.from_user.id}")
    
    await state.clear()
    
    text = """
<b>⚙️ Настройка реквизитов</b>

Давайте пошагово заполним ваши данные для создания платежей.

<b>📋 Что нам понадобится:</b>
• Страна назначения
• Банк получателя
• Номер карты получателя

<b>🚀 Начнем с выбора страны назначения:</b>
    """
    
    await message.answer(text, reply_markup=get_countries_keyboard())

@dp.callback_query(F.data.startswith("country_"))
async def process_country_selection(callback: CallbackQuery, state: FSMContext):
    """Process country selection"""
    country_code = callback.data.split("_", 1)[1]
    
    await state.update_data(country=country_code)
        
    country_names = {
        'tajikistan': 'Таджикистан 🇹🇯',
        'georgia': 'Грузия 🇬🇪', 
        'kyrgyzstan': 'Киргизия 🇰🇬'
    }
    
    country_name = country_names.get(country_code, country_code)
    
    text = f"""
<b>✅ Выбрана страна: {country_name}</b>

Теперь выберите банк получателя:
    """
    
    await callback.message.edit_text(text, reply_markup=get_banks_keyboard(country_code))
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected country: {country_code}")

@dp.callback_query(F.data.startswith("bank_"))
async def process_bank_selection(callback: CallbackQuery, state: FSMContext):
    """Process bank selection"""
    bank_code = callback.data.split("_", 1)[1]
    
    bank_names = {
        'korti_milli': 'Корти Милли',
        'azizi_molia': 'Азизи-Молия',
        'bank_arvand': 'Банк Арванд', 
        'eskhata_bank': 'Эсхата Банк',
        'bog_bank': 'Bank of Georgia',
        'tbc_bank': 'TBC Bank',
        'optima_bank': 'Оптима Банк',
        'demir_bank': 'Демир Банк'
    }
    
    bank_name = bank_names.get(bank_code, bank_code)
    
    user_data = await state.get_data()
    await state.update_data(
        country=user_data.get('country'),
        bank=bank_code,
        bank_name=bank_name
    )
    
    text = f"""
<b>✅ Выбран банк: {bank_name}</b>

<b>💳 Теперь введите номер карты получателя:</b>

Пример: 1234 5678 9012 3456
(можно вводить с пробелами или без)

<b>📝 Для тестирования введите любой 16-значный номер!</b>
    """
    
    await callback.message.edit_text(text)
    await callback.answer()
    await state.set_state(RequisitesStates.waiting_for_card)
    logger.info(f"User {callback.from_user.id} selected bank: {bank_code}")

@dp.callback_query(F.data == "back_to_countries")
async def back_to_countries(callback: CallbackQuery, state: FSMContext):
    """Back to country selection"""
    await state.clear()
    
    text = """
<b>⚙️ Настройка реквизитов</b>

<b>🚀 Выберите страну назначения:</b>
    """
    
    await callback.message.edit_text(text, reply_markup=get_countries_keyboard())
    await callback.answer()

@dp.message(RequisitesStates.waiting_for_card)
async def process_card_number(message: Message, state: FSMContext):
    """Process card number input"""
    try:
        logger.info(f"🔄 Processing card number for user {message.from_user.id}")
        
        # Validate card number
        if not validate_card_number(message.text):
            logger.warning(f"❌ Invalid card format: {message.text}")
            await message.answer(
                "❌ <b>Неверный формат номера карты!</b>\n\n"
                "Введите номер карты из 16 цифр.\n"
                "Пример: 1234 5678 9012 3456"
            )
            return
        
        # Format card number
        formatted_card = format_card_number(message.text)
        logger.info(f"✅ Card formatted: {formatted_card}")
        
        # Get user data from state
        user_data = await state.get_data()
        country = user_data.get('country', 'unknown')
        bank = user_data.get('bank', 'unknown')
        bank_name = user_data.get('bank_name', 'Unknown')
        
        logger.info(f"📋 User data: country={country}, bank={bank}")
        
        # Save to database using new async repository
        async with AsyncSessionLocal() as session:
            try:
                # Create/get user
                user_repo = UserRepository(session)
                user = await user_repo.get_or_create_user(
                    user_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                
                # Save requisites
                requisites_repo = UserRequisitesRepository(session)
                success = await requisites_repo.upsert_requisites(
                    user_id=message.from_user.id,
                    recipient_card=formatted_card,
                    country=country,
                    bank=bank
                )
                
                if success:
                    country_names = {
                        'tajikistan': 'Таджикистан 🇹🇯',
                        'georgia': 'Грузия 🇬🇪', 
                        'kyrgyzstan': 'Киргизия 🇰🇬'
                    }
                    country_display = country_names.get(country, country.title())
                    
                    confirmation_text = f"""
✅ <b>Реквизиты успешно сохранены!</b>

<b>📋 Ваши данные:</b>
• Страна: <code>{country_display}</code>
• Банк: <code>{bank_name}</code>
• Карта: <code>{formatted_card}</code>

<b>🎉 Отлично!</b> Теперь вы можете создавать платежи командой:

<code>/payment [сумма]</code>

<b>Примеры:</b>
• <code>/payment 5000</code> - платеж на 5000 рублей
• <code>/payment 1500</code> - платеж на 1500 рублей

<b>⚡ Следующий шаг:</b>
Попробуйте создать тестовый платеж!
                    """
                    
                    await message.answer(confirmation_text)
                    await state.clear()
                    
                    logger.info(f"✅ User {message.from_user.id} requisites saved successfully")
                else:
                    logger.error(f"❌ Failed to save requisites for user {message.from_user.id}")
                    await message.answer(
                        "❌ <b>Ошибка сохранения!</b>\n\n"
                        "Не удалось сохранить реквизиты.\n"
                        "Попробуйте еще раз или обратитесь к администратору."
                    )
                    
            except Exception as db_error:
                logger.error(f"💥 Database error: {db_error}")
                await message.answer(
                    f"❌ <b>Ошибка базы данных!</b>\n\n"
                    f"Техническая информация: {str(db_error)}\n\n"
                    "Попробуйте еще раз или обратитесь к администратору."
                )
                
    except Exception as e:
        logger.error(f"💥 Critical error in process_card_number: {e}")
        await message.answer(
            f"❌ <b>Критическая ошибка!</b>\n\n"
            f"Техническая информация: {str(e)}\n\n"
            "Попробуйте еще раз позже."
        )
        await state.clear()

@dp.message(Command("payment"))
async def command_payment_handler(message: Message) -> None:
    """Handler for /payment command"""
    try:
        # Parse amount from command
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.answer(
                "❌ <b>Укажите сумму платежа!</b>\n\n"
                "<b>Правильный формат:</b>\n"
                "<code>/payment [сумма]</code>\n\n"
                "<b>Примеры:</b>\n"
                "• <code>/payment 5000</code>\n"
                "• <code>/payment 1500</code>"
            )
            return
        
        try:
            amount = float(command_parts[1])
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            await message.answer(
                "❌ <b>Неверная сумма!</b>\n\n"
                "Введите положительное число.\n"
                "Пример: <code>/payment 5000</code>"
            )
            return
        
        # Check limits
        min_amount = 300
        max_amount = 120000
        
        if amount < min_amount:
            await message.answer(
                f"❌ <b>Сумма слишком мала!</b>\n\n"
                f"Минимальная сумма: <code>{min_amount}</code> рублей"
            )
            return
            
        if amount > max_amount:
            await message.answer(
                f"❌ <b>Сумма слишком велика!</b>\n\n"
                f"Максимальная сумма: <code>{max_amount}</code> рублей"
            )
            return
        
        # Check user requisites
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            user_requisites = await user_repo.get_user_requisites(message.from_user.id)
            
            if not user_requisites:
                await message.answer(
                    "❌ <b>Реквизиты не настроены!</b>\n\n"
                    "Сначала настройте ваши данные командой /settings"
                )
                return
            
            country_names = {
                'tajikistan': 'Таджикистан 🇹🇯',
                'georgia': 'Грузия 🇬🇪', 
                'kyrgyzstan': 'Киргизия 🇰🇬'
            }
            country_display = country_names.get(user_requisites.country, user_requisites.country.title())
            
            # Show processing message
            processing_text = f"""
🔄 <b>Создаем платеж на {amount:,.0f} рублей...</b>

<b>📋 Ваши реквизиты:</b>
• Страна: <code>{country_display}</code>
• Банк: <code>{user_requisites.bank}</code>
• Карта: <code>{user_requisites.recipient_card}</code>

<b>🤖 Запускаем браузерную автоматизацию...</b>
• Открываем multitransfer.ru
• Заполняем формы автоматически  
• Обходим блокировки через прокси
• Получаем QR-код для оплаты

<i>Это может занять 30-60 секунд...</i>
            """
            
            processing_message = await message.answer(processing_text)
            
            try:
                logger.info(f"🚀 Starting payment automation for user {message.from_user.id}")
                
                # Create payment using PaymentService
                payment_service = PaymentService(session)
                result = await payment_service.create_payment(
                    user_id=message.from_user.id,
                    amount=amount,
                    currency_from="RUB",
                    currency_to="TJS"
                )
                
                if result['status'] == 'success':
                    # SUCCESS - Payment created!
                    success_text = f"""
✅ <b>Платеж успешно создан!</b>

<b>💰 Сумма:</b> {amount:,.0f} рублей
<b>🏦 Получатель:</b> {country_display}, {user_requisites.bank}
<b>💳 Карта:</b> {user_requisites.recipient_card}

<b>🎯 Для оплаты:</b>"""
                    
                    # Add QR code if available
                    if result.get('qr_code_url'):
                        success_text += f"\n📱 <a href=\"{result['qr_code_url']}\">QR-код для оплаты</a>"
                    
                    # Add payment URL if available
                    if result.get('payment_url'):
                        success_text += f"\n🔗 <a href=\"{result['payment_url']}\">Ссылка для оплаты</a>"
                    
                    # Add payment ID if available
                    if result.get('payment_id'):
                        success_text += f"\n\n<b>📋 ID платежа:</b> <code>{result['payment_id']}</code>"
                    
                    success_text += f"\n\n<b>⏱️ Время обработки:</b> {result.get('processing_time', 0):.1f} сек"
                    success_text += f"\n<b>👤 Паспорт:</b> {result.get('passport_used', 'N/A')}"
                    success_text += "\n\n<b>💡 Совет:</b> Сохраните QR-код и оплатите в удобное время!"
                    
                    await processing_message.edit_text(success_text, disable_web_page_preview=False)
                    logger.info(f"✅ Payment successful for user {message.from_user.id}")
                    
                else:
                    # FAILURE - Show error
                    error_text = f"""
❌ <b>Не удалось создать платеж</b>

<b>💰 Сумма:</b> {amount:,.0f} рублей
<b>🏦 Получатель:</b> {country_display}, {user_requisites.bank}

<b>🔥 Причина ошибки:</b>
<code>{result.get('error', 'Неизвестная ошибка')}</code>

<b>🔄 Что делать:</b>
• Попробуйте еще раз через 1-2 минуты
• Проверьте корректность реквизитов (/settings)
• Обратитесь к администратору, если проблема повторяется

<b>⏱️ Время попытки:</b> {result.get('processing_time', 0):.1f} сек
                    """
                    
                    await processing_message.edit_text(error_text)
                    logger.error(f"❌ Payment failed for user {message.from_user.id}: {result.get('error')}")
                    
            except PaymentError as payment_error:
                # Payment service error
                error_text = f"""
💥 <b>Ошибка создания платежа</b>

<b>💰 Сумма:</b> {amount:,.0f} рублей

<b>🔥 Ошибка:</b>
<code>{str(payment_error)}</code>

<b>🔄 Действия:</b>
• Попробуйте позже (возможны технические работы)
• Проверьте реквизиты командой /settings
• Обратитесь к администратору при повторных ошибках

<b>🌐 Ссылка на сайт:</b>
<a href="https://multitransfer.ru">multitransfer.ru</a>
                """
                
                await processing_message.edit_text(error_text)
                logger.error(f"💥 Payment error: {payment_error}")
                
            except Exception as automation_error:
                # CRITICAL ERROR
                error_text = f"""
💥 <b>Критическая ошибка автоматизации</b>

<b>💰 Сумма:</b> {amount:,.0f} рублей

<b>🔥 Техническая ошибка:</b>
<code>{str(automation_error)}</code>

<b>🔄 Действия:</b>
• Попробуйте позже (возможны технические работы)
• Сообщите администратору об ошибке
• Используйте ручное создание платежа на сайте

<b>🌐 Ссылка на сайт:</b>
<a href="https://multitransfer.ru">multitransfer.ru</a>
                """
                
                await processing_message.edit_text(error_text)
                logger.error(f"💥 Critical automation error: {automation_error}")
        
        logger.info(f"Payment request completed: user {message.from_user.id}, amount {amount}")
        
    except Exception as e:
        logger.error(f"Error in payment handler: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка!</b>\n\n"
            "Попробуйте еще раз позже."
        )

@dp.message()
async def echo_handler(message: Message) -> None:
    """Handler for all other messages"""
    if message.text:
        echo_text = f"""
Получил ваше сообщение: <i>{message.text}</i>

<b>📋 Доступные команды:</b>
• /help - справка
• /settings - настройки  
• /payment [сумма] - создать платеж

<b>Пример:</b> <code>/payment 5000</code>
        """
        await message.answer(echo_text)

async def on_startup():
    """Actions to perform on bot startup"""
    logger.info("🚀 Starting MultiTransfer Bot...")
    
    # Create necessary directories
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("logs/automation").mkdir(exist_ok=True)
    
    # Initialize database
    await init_database()
    
    logger.info("✅ Bot started successfully!")

async def on_shutdown():
    """Actions to perform on bot shutdown"""
    logger.info("🛑 Shutting down MultiTransfer Bot...")
    await bot.session.close()

async def main() -> None:
    """Main function to run the bot"""
    global config, bot
    
    try:
        # Load configuration
        config = get_config()
        
        # Initialize bot
        bot = Bot(
            token=config.telegram['token'],
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            )
        )
        
        await on_startup()
        
        # Start polling
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed with error: {e}")
        raise
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"💥 Failed to start bot: {e}")
        sys.exit(1)