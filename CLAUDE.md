# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Telegram bot that automates payment processing through multitransfer.ru. The bot allows users to configure recipient details and automatically creates transfers using browser automation with Selenium.

## Project Structure

- `main.py` - Main bot entry point with aiogram handlers
- `core/` - Core business logic
  - `config.py` - Configuration management with YAML and environment variables
  - `database/` - SQLAlchemy models and repositories
  - `services/payment_service.py` - Main payment processing service
  - `proxy/` - Proxy management for browser automation
- `web/` - Browser automation components
  - `browser/multitransfer.py` - Selenium automation for multitransfer.ru
  - `captcha/` - CAPTCHA solving integration
- `bot/` - Telegram bot components (handlers, keyboards, states)
- `utils/` - Validation and helper utilities
- `data/` - SQLite database and passport data for form filling

## Key Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py

# Test proxy configuration (disable VPN first!)
curl --proxy http://GALsB4:6UwJ3b@196.16.220.52:8000 http://httpbin.org/ip

# Run automation test with proxy
PYTHONPATH=. python3 tests/automation/test_complete_automation.py

# Enable/disable proxy for testing
rm -f /tmp/proxy_disabled  # Enable proxy
touch /tmp/proxy_disabled  # Disable proxy

# Monitor proxy logs
tail -f logs/app.log | grep -i proxy
```

### Database
The bot uses SQLite by default (`data/bot.db`). Database migrations are handled through SQLAlchemy's `create_all()` method in `main.py:init_database()`.

### Environment Setup
1. Copy `.env.example` to `.env` (if exists)
2. Set required environment variables:
   - `BOT_TOKEN` - Telegram bot token
   - `PROXY_API_KEY` - Proxy service API key (optional for development)
   - `CAPTCHA_API_KEY` - CAPTCHA service API key (optional)

## Architecture

### Payment Flow
1. User configures recipient details via the `/settings` command, which uses an FSM flow
2. User initiates payment with the `/payment [amount]` command
3. `PaymentService` validates the request and retrieves the next available sender profile using the smart rotation logic
4. `MultiTransferAutomation` launches a browser with a fresh proxy (German SOCKS5 priority), fills all forms, and solves captchas if they appear
5. The final result (QR code, payment URL) or an error message is returned to the user

### Browser Automation
The `MultiTransferAutomation` class in `web/browser/multitransfer.py` handles an 11-step process:
1. Click "ПЕРЕВЕСТИ ЗА РУБЕЖ"
2. Select destination country (Tajikistan/Georgia/Kyrgyzstan)
3. Fill in the transfer amount with human-like typing
4. Select the destination currency (TJS/GEL/KGS)
5. Choose the transfer method (bank selection)
6. Click "Продолжить" to proceed to the main form
7. Fill in the recipient's card number
8. Fill in the sender's passport and personal data
9. Critically, locate and click the "accept terms" checkbox. This step uses a robust multi-selector strategy to ensure reliability
10. Submit the final form
11. Solve a CAPTCHA if it appears after submission

### Data Rotation Logic
Instead of being purely random, passport data usage is managed intelligently to maximize success rates:
- The system uses one sender profile repeatedly until an error occurs
- The `PassportStats` table tracks `success_count` and `error_count` for each profile
- Upon failure, the system rotates to the next available profile, prioritizing those with a lower error rate

### Database Models
- `User` - Telegram user information
- `UserRequisites` - Recipient bank details per user
- `PaymentHistory` - Records of all payment attempts, including status and processing time
- `PassportData` - The pool of sender personal data loaded from the Excel file
- `PassportStats` - Tracks usage statistics for each sender profile to enable smart rotation

### Configuration
All configuration is managed through `config.yml` with environment variable substitution using `${VAR_NAME}` syntax. The `Config` class provides dot-notation access (e.g., `config.get('telegram.token')`).

## Testing

Test files are located in `tests/automation/`. The `test_complete_automation.py` file contains a full end-to-end test that validates the browser automation flow without actually creating payments.

## Performance Target

The primary performance target is to process a payment request (from command to QR code) in under 40 seconds. This is achieved through optimized selectors, parallel operations where possible, and minimizing unnecessary delays.

## Development Notes

- Browser automation uses undetected-chromedriver to minimize the risk of detection by anti-bot systems
- The bot uses aiogram 3's FSM (Finite State Machine) for managing conversational flows, such as collecting recipient details
- Proxy rotation is implemented in `core/proxy/manager.py` to automatically switch proxies upon failure
- All significant browser interactions include human-like delays and typing patterns to appear more natural
- The bot supports multiple countries and banks (configured in `config.yml`)
- Screenshots are automatically saved to `logs/automation/` during automation runs

## Deployment

The project includes Docker configuration and can be deployed to Railway or similar platforms. The `Dockerfile` sets up the Python environment and Chrome dependencies needed for browser automation.