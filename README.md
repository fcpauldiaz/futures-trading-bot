# Webhook Trading Handler

FastAPI service that receives webhook requests and executes trading orders via webhook URLs.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your webhook URLs:

```bash
cp .env.example .env
```

Edit `.env` and add your webhook URLs and trading configuration.

3. Run the webhook handler:

```bash
python main.py
```

The service will start on `http://0.0.0.0:8000`

## Configuration

* `TRADING_MODE`: Set to "paper" for paper trading or "live" for live trading
* Webhook URLs are read from `.env` file or environment variables
* Trading configuration (ticker symbols, quantities) are in `config.py`

## API Endpoints

* `POST /gold-trend` - Update gold trend (bullish/bearish)
* `POST /gold` - Handle gold trading webhooks (bullish_entry, bearish_entry, exit)
* `POST /nq` - Handle NQ trading webhooks (bullish_entry, bearish_entry, exit)
* `POST /fbd` - Handle FBD webhook payloads (Long Triggered, Target Hit, Stop Loss messages)

## Features

* FastAPI REST API for receiving webhook requests
* Parses trading messages from webhook payloads (Long Triggered, Target Hit, Stop Loss)
* Handles multiple strategies (MES, Gold, NQ)
* Executes market orders via webhook URLs
* Position tracking for all strategies
* Comprehensive logging

## Project Structure

* `main.py` - FastAPI application with webhook endpoints and handler functions
* `config.py` - Centralized configuration (webhook URLs, trading config)
* `message_parser.py` - Message parsing and pattern matching
* `order_executor.py` - Order execution via webhooks
* `position_tracker.py` - Position and order tracking
* `csv_logger.py` - Logging functionality

## About

Webhook handler service that receives trading signals via HTTP webhooks and executes orders through webhook integration.

