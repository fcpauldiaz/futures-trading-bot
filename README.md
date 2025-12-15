# Discord Trading Bot

Automated trading bot that monitors Discord channels for trading signals and executes market orders via webhooks.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Discord tokens:

```bash
cp .env.example .env
```

Edit `.env` and add your Discord tokens and channel IDs.

3. Run the bot:

```bash
python main.py
```

## Configuration

* `TRADING_MODE`: Set to "paper" for paper trading or "live" for live trading
* Discord tokens are read from `.env` file or environment variables
* Webhook URLs and account configurations are in `config.py`

## Features

* Monitors Discord channels every 5 seconds
* Parses trading messages (BOUGHT/SOLD format, Long Triggered, Target Hit, Stop Loss)
* Handles multiple strategies (MES, Gold, NQ)
* Places market orders via webhook URLs
* Logs successful trades to CSV
* Comprehensive logging to file and console
* FastAPI endpoints for webhook integration (`/gold`, `/nq`, `/fbd`)

## Project Structure

* `main.py` - Application entry point with FastAPI app and handler functions
* `config.py` - Centralized configuration
* `discord_scraper.py` - Discord API interaction
* `message_parser.py` - Message parsing and pattern matching
* `order_executor.py` - Order execution via webhooks
* `position_tracker.py` - Position and order tracking
* `csv_logger.py` - Logging functionality

## About

Automated trading bot that monitors Discord channels for trading signals and executes orders via webhook integration.

