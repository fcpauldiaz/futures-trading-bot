import logging
import csv
import os
from datetime import datetime
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

CSV_LOG_FILE = "trades.csv"

def ensure_csv_header():
    if not os.path.exists(CSV_LOG_FILE):
        with open(CSV_LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'ticker', 'action', 'quantity', 'price', 
                'order_type', 'source', 'result'
            ])

def log_trade(
    ticker: str,
    action: str,
    quantity: int,
    price: Optional[float] = None,
    order_type: Optional[str] = None,
    source: Optional[str] = None,
    result: Optional[str] = None
):
    ensure_csv_header()
    
    with open(CSV_LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            ticker,
            action,
            quantity,
            price or '',
            order_type or '',
            source or '',
            result or ''
        ])
    
    logger.info(f"Trade logged: {ticker} {action} {quantity} @ {price}")

