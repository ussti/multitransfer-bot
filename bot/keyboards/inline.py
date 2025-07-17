"""
Inline keyboards for MultiTransfer Bot
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import get_config

config = get_config()

def get_countries_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with supported countries"""
    buttons = []
    
    for country_code, country_data in config.multitransfer['supported_countries'].items():
        buttons.append([
            InlineKeyboardButton(
                text=f"🇹🇯 {country_data['name']}" if country_code == 'tajikistan'
                else f"🇬🇪 {country_data['name']}" if country_code == 'georgia'
                else f"🇰🇬 {country_data['name']}",
                callback_data=f"country_{country_code}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_banks_keyboard(country_code: str) -> InlineKeyboardMarkup:
    """Get keyboard with banks for selected country"""
    country_data = config.multitransfer['supported_countries'].get(country_code)
    if not country_data:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    buttons = []
    bank_names = {
        'korti_milli': '🏦 Корти Милли',
        'azizi_molia': '🏦 Азизи-Молия', 
        'bank_arvand': '🏦 Банк Арванд',
        'eskhata_bank': '🏦 Эсхата Банк',
        'bog_bank': '🏦 Bank of Georgia',
        'tbc_bank': '🏦 TBC Bank',
        'optima_bank': '🏦 Оптима Банк',
        'demir_bank': '🏦 Демир Банк'
    }
    
    for bank_code in country_data['banks']:
        bank_name = bank_names.get(bank_code, bank_code)
        buttons.append([
            InlineKeyboardButton(
                text=bank_name,
                callback_data=f"bank_{bank_code}"
            )
        ])
    
    # Add back button
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад к выбору страны",
            callback_data="back_to_countries"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Get confirmation keyboard"""
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Все верно, сохранить",
                callback_data="confirm_requisites"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data="edit_requisites"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data="cancel_requisites"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_currencies_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with supported currencies"""
    buttons = []
    
    currency_emojis = {
        'RUB': '🇷🇺',
        'USD': '🇺🇸', 
        'EUR': '🇪🇺',
        'TJS': '🇹🇯',
        'KGS': '🇰🇬',
        'GEL': '🇬🇪'
    }
    
    for currency in config.multitransfer['supported_currencies']:
        emoji = currency_emojis.get(currency, '💱')
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {currency}",
                callback_data=f"currency_{currency}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard"""
    buttons = [
        [
            InlineKeyboardButton(
                text="⚙️ Настроить реквизиты",
                callback_data="setup_requisites"
            )
        ],
        [
            InlineKeyboardButton(
                text="💰 Создать платеж",
                callback_data="create_payment"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Мои реквизиты",
                callback_data="view_requisites"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 История платежей",
                callback_data="payment_history"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)