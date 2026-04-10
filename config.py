import os
import re
from dotenv import load_dotenv

load_dotenv()

TICKER_SYMBOL = "MES"
GLOBAL_QUANTITY = int(os.getenv("GLOBAL_QUANTITY", "15"))
GLOBAL_REMAINING_QTY = 3

GOLD_TICKER = "MGCJ26"
GOLD_QUANTITY = int(os.getenv("GOLD_QUANTITY", "4"))

NQ_TICKER = "MNQ"
NQ_QUANTITY = int(os.getenv("NQ_QUANTITY", "6"))

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
GOLD_WEBHOOK_URL = os.getenv("GOLD_WEBHOOK_URL", "")
NQ_WEBHOOK_URL = os.getenv("NQ_WEBHOOK_URL", "")
GENERAL_CHANNEL_WEBHOOK_URL = os.getenv("GENERAL_CHANNEL_WEBHOOK_URL", "")

ORDER_FILE = "open_order.json"
GOLD_ORDER_FILE = "open_gold_order.json"
NQ_ORDER_FILE = "open_nq_order.json"

LONG_TRIGGERED_PATTERN = re.compile(
    r"Ticker: \*\*([^*]+)\*\*\s*\nInterval: \*\*(\d+)\*\*\s*\nLevel: \*\*([\d.]+)\*\*\s*\nScore: \*\*(\d+/\d+)\*\*\s*\nPrice: \*\*([\d.]+)\*\*\s*\nTime: \*\*([\d\s:-]+)\*\*",
    re.IGNORECASE | re.MULTILINE
)

TARGET_HIT_PATTERN = re.compile(
    r"Ticker: \*\*([^*]+)\*\*\s*\nInterval: \*\*(\d+)\*\*\s*\nLevel: \*\*([\d.]+)\*\*\s*\nTarget 1: \*\*([\d.]+)\*\*\s*\nEntry: \*\*([\d.]+)\*\*\s*\nProfit: \*\*([+-]?[\d.]+) pts\*\*\s*\nTime: \*\*([\d\s:-]+)\*\*",
    re.IGNORECASE | re.MULTILINE
)

TARGET2_HIT_PATTERN = re.compile(
    r"Ticker: \*\*([^*]+)\*\*\s*\nInterval: \*\*(\d+)\*\*\s*\nLevel: \*\*([\d.]+)\*\*\s*\nTarget 2: \*\*([\d.]+)\*\*\s*\nEntry: \*\*([\d.]+)\*\*\s*\nProfit: \*\*([+-]?[\d.]+) pts\*\*\s*\nTime: \*\*([\d\s:-]+)\*\*",
    re.IGNORECASE | re.MULTILINE
)

STOP_LOSS_PATTERN = re.compile(
    r"Stop Loss Hit\s*\nTicker: \*\*([^*]+)\*\*\s*\nInterval: \*\*(\d+)\*\*\s*\nLevel: \*\*([\d.]+)\*\*\s*\nEntry: \*\*([\d.]+)\*\*\s*\nExit: \*\*([\d.]+)\*\*\s*\nLoss: \*\*([+-]?[\d.]+) pts\*\*\s*\nTime: \*\*([\d\s:-]+)\*\*",
    re.IGNORECASE | re.MULTILINE
)

STOP_LOSS_SIMPLE_PATTERN = re.compile(
    r"Ticker: \*\*([^*]+)\*\*\s*\nInterval: \*\*(\d+)\*\*\s*\nLevel: \*\*([\d.]+)\*\*\s*\nEntry: \*\*([\d.]+)\*\*\s*\nExit: \*\*([\d.]+)\*\*\s*\nLoss: \*\*([+-]?[\d.]+) pts\*\*",
    re.IGNORECASE | re.MULTILINE
)

TRADING_MODE = os.getenv("TRADING_MODE", "paper")

TRADINGVIEW_ARM_TTL_SECONDS = int(os.getenv("TRADINGVIEW_ARM_TTL_SECONDS", "600"))

TRADINGVIEW_DTR_ARM_PATTERN = re.compile(
    r"DTR\s+9AM\s*[—\-–]\s*IFVG\s*[▼▲]\s*(SHORT|LONG)\s+confirmed",
    re.IGNORECASE,
)

TRADINGVIEW_TSR_ARM_PATTERN = re.compile(
    r"TSR\s+CR:\s*(SHORT|LONG)\s+signal\s+triggered",
    re.IGNORECASE,
)

TRADINGVIEW_NQ_ENTRY_PATTERN = re.compile(
    r"NQ1!\s*\(\d+\)\s*\|\s*(SELL|LONG)\s+at\s+([\d.]+)",
    re.IGNORECASE,
)

TRADINGVIEW_NQ_EXIT_PATTERN = re.compile(
    r"NQ1!\s*\(\d+\)\s*\|\s*EXIT\s+(LONG|SHORT)\s+at\s+([\d.]+)",
    re.IGNORECASE,
)

TRADINGVIEW_NQ_STOP_LOSS_PATTERN = re.compile(
    r"NQ1!\s*\(\d+\)\s*\|\s*STOP\s+LOSS\s+hit\s+at\s+([\d.]+)",
    re.IGNORECASE,
)

