"""
FSM States for user requisites input
Handles step-by-step data collection process
"""

from aiogram.fsm.state import State, StatesGroup

class RequisitesStates(StatesGroup):
    """States for collecting user requisites"""
    
    # Country and destination selection
    waiting_for_country = State()
    waiting_for_bank = State()
    waiting_for_recipient_card = State()
    
    # Sender passport information
    waiting_for_passport_series = State()
    waiting_for_passport_number = State()
    waiting_for_passport_date = State()
    
    # Personal information
    waiting_for_surname = State()
    waiting_for_name = State()
    waiting_for_patronymic = State()
    waiting_for_birthdate = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    
    # Confirmation
    waiting_for_confirmation = State()

class PaymentStates(StatesGroup):
    """States for payment creation process"""
    
    waiting_for_amount = State()
    waiting_for_currency = State()
    processing_payment = State()
    payment_completed = State()