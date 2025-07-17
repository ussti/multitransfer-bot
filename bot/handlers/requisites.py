"""
Handlers for user requisites management
Step-by-step data collection process
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from bot.states.requisites import RequisitesStates
from bot.keyboards.inline import (
    get_countries_keyboard, 
    get_banks_keyboard,
    get_confirmation_keyboard,
    get_main_menu_keyboard
)
from utils.validators import (
    validate_card_number,
    validate_passport_series, 
    validate_passport_number,
    validate_date,
    validate_name,
    validate_phone,
    format_card_number,
    format_phone
)

router = Router()

@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """Start requisites setup process"""
    print(f"🔥 SETTINGS COMMAND RECEIVED from user {message.from_user.id}")  # ОТЛАДКА
    await state.clear()
    
    text = """
<b>⚙️ Настройка реквизитов</b>

Давайте пошагово заполним ваши данные для создания платежей.

<b>📋 Что нам понадобится:</b>
• Страна назначения
• Номер карты получателя
• Ваши паспортные данные
• Контактная информация

<b>🚀 Начнем с выбора страны назначения:</b>
    """
    
    await message.answer(text, reply_markup=get_countries_keyboard())
    await state.set_state(RequisitesStates.waiting_for_country)

@router.callback_query(F.data.startswith("country_"), RequisitesStates.waiting_for_country)
async def process_country_selection(callback: CallbackQuery, state: FSMContext):
    """Process country selection"""
    country_code = callback.data.split("_", 1)[1]
    
    # Save country to state
    await state.update_data(country=country_code)
    
    from core.config import get_config
    config = get_config()
    country_data = config.multitransfer['supported_countries'].get(country_code)
    
    if not country_data:
        await callback.answer("❌ Неизвестная страна")
        return
    
    text = f"""
<b>✅ Выбрана страна: {country_data['name']}</b>

Теперь выберите банк получателя:
    """
    
    await callback.message.edit_text(text, reply_markup=get_banks_keyboard(country_code))
    await state.set_state(RequisitesStates.waiting_for_bank)
    await callback.answer()

@router.callback_query(F.data == "back_to_countries", RequisitesStates.waiting_for_bank)
async def back_to_countries(callback: CallbackQuery, state: FSMContext):
    """Back to country selection"""
    text = """
<b>⚙️ Настройка реквизитов</b>

<b>🚀 Выберите страну назначения:</b>
    """
    
    await callback.message.edit_text(text, reply_markup=get_countries_keyboard())
    await state.set_state(RequisitesStates.waiting_for_country)
    await callback.answer()

@router.callback_query(F.data.startswith("bank_"), RequisitesStates.waiting_for_bank)
async def process_bank_selection(callback: CallbackQuery, state: FSMContext):
    """Process bank selection"""
    bank_code = callback.data.split("_", 1)[1]
    
    # Save bank to state
    await state.update_data(bank=bank_code)
    
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
    
    text = f"""
<b>✅ Выбран банк: {bank_name}</b>

<b>💳 Теперь введите номер карты получателя:</b>

Пример: 1234 5678 9012 3456
(можно вводить с пробелами или без)
    """
    
    await callback.message.edit_text(text)
    await state.set_state(RequisitesStates.waiting_for_recipient_card)
    await callback.answer()

@router.message(RequisitesStates.waiting_for_recipient_card)
async def process_recipient_card(message: Message, state: FSMContext):
    """Process recipient card number"""
    card_number = message.text.strip()
    
    is_valid, error_msg = validate_card_number(card_number)
    
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nПопробуйте еще раз:")
        return
    
    # Save formatted card number
    formatted_card = format_card_number(card_number)
    await state.update_data(recipient_card=formatted_card)
    
    text = f"""
<b>✅ Номер карты получателя: {formatted_card}</b>

<b>📋 Теперь заполним ваши паспортные данные</b>

<b>🆔 Введите серию паспорта РФ (4 цифры):</b>

Пример: 1234
    """
    
    await message.answer(text)
    await state.set_state(RequisitesStates.waiting_for_passport_series)

# Добавим несколько основных обработчиков для теста
@router.message(RequisitesStates.waiting_for_passport_series)
async def process_passport_series(message: Message, state: FSMContext):
    """Process passport series"""
    series = message.text.strip()
    
    is_valid, error_msg = validate_passport_series(series)
    
    if not is_valid:
        await message.answer(f"❌ {error_msg}\n\nПопробуйте еще раз:")
        return
    
    await state.update_data(passport_series=series)
    
    text = f"""
<b>✅ Серия паспорта: {series}</b>

<b>🎉 Отлично! Базовая настройка работает!</b>

Полная версия ввода реквизитов будет добавлена далее.
Пока что система успешно:
• Показывает страны
• Выбирает банки  
• Принимает номер карты
• Валидирует паспорт

<b>Тестирование завершено! ✅</b>
    """
    
    await message.answer(text)
    await state.clear()