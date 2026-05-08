---
title: BluekingQuotexBot
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🚀 Antigravity: Production-Ready Quotex Auto-Trading Bot

Antigravity is a high-performance, autonomous trading infrastructure built for Windows environments. It leverages the `pyquotex` library to interface with the Quotex platform, executing trades based on dynamic strategies with real-time monitoring and Telegram integration.

## 🏗️ Architecture Overview

The system is built on an asynchronous, modular architecture:

- **Core Engine (`core/trading_engine.py`)**: The heart of the bot. Orchestrates data collection, signal generation, and execution.
- **Broker Wrapper (`core/broker.py`)**: Low-level interface with Quotex API. Handles session persistence and automatic reconnection.
- **Strategy Parser (`core/strategy_parser.py`)**: Real-time monitor for `strategy.txt`. Hot-reloads trading parameters without downtime.
- **Risk Manager (`core/risk_manager.py`)**: Implements Martingale, Stop Loss, and Take Profit logic to protect capital.
- **Indicator Engine (`indicators/engine.py`)**: High-speed technical analysis using `pandas_ta`.
- **Telegram Bot (`telegram/bot.py`)**: Complete command & control interface with dashboard-style notifications.

## 📂 Project Structure

```text
antigravity/
├── main.py                # Entry point
├── strategy.txt           # Active strategy (dynamically reloaded)
├── .env                   # Sensitive credentials
├── requirements.txt       # Dependencies
├── core/
│   ├── broker.py          # API interaction
│   ├── strategy_parser.py # File monitoring
│   ├── trading_engine.py  # Orchestration
│   └── risk_manager.py    # Protection logic
├── telegram/
│   └── bot.py             # Bot handlers
├── strategies/            # Example strategy files
├── indicators/
│   └── engine.py          # Technical analysis
├── logs/                  # Bot logs
├── storage/               # Trade history (JSON)
└── utils/                 # Helpers
```

## 🛠️ Setup Instructions (Windows)

1. **Install Python**: Ensure Python 3.12+ is installed and added to PATH.
2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   - Edit `.env` with your Quotex credentials and Telegram Bot details.
   - To get a Telegram Bot Token, use [@BotFather](https://t.me/botfather).
   - To get your Chat ID, use [@userinfobot](https://t.me/userinfobot).
4. **Define Strategy**:
   - Edit `strategy.txt` with your desired parameters (see examples in `strategies/`).

## 🚀 Running Instructions

Start the bot:
```powershell
python main.py
```

The bot will automatically:
1. Connect to Quotex (Demo by default).
2. Start the Telegram interface.
3. Monitor `strategy.txt` for changes.
4. Execute trades when signals align.

## 🤖 Telegram Bot Guide

### Commands:
- `/status`: Real-time dashboard (Uptime, Profit, Win Rate).
- `/balance`: Check account balance.
- `/wins` / `/losses`: Summary of results.
- `/pause` / `/resume`: Manual control over the engine.
- `/strategy`: View active trading parameters.

### Notifications:
- 🚀 Startup/Shutdown alerts.
- 🔔 Signal detection alerts.
- 🎯 Execution confirmation.
- 💰 Win/Loss results with profit tracking.
- ⚠️ Risk management triggers (Stop Loss/Take Profit).

## 🛡️ Risk Management & Security

- **Capital Protection**: Never trade more than you can afford to lose. Use the `STOP_LOSS` parameter in your strategy.
- **Security**: Keep your `.env` file private. Never share your Quotex password or Telegram token.
- **Environment**: Always test new strategies on `DEMO` before switching to `REAL` in `.env`.
- **Cooldown**: Use `COOLDOWN_SECONDS` to prevent over-trading in volatile markets.

## 🔮 Future Upgrades
- Multi-pair simultaneous trading.
- Advanced ML-based signal filtering.
- Web-based dashboard for advanced analytics.
- Integration with more indicators (MACD, Bollinger Bands).

---
*Disclaimer: Trading involves significant risk. This bot is for educational and research purposes only. Use at your own risk.*
