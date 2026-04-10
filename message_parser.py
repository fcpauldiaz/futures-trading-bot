import json
import re
import hashlib
from typing import Literal, Optional, Match, TypedDict
import config

processed_messages = set()

def create_message_id(ticker: str, target_price: float, entry_price: float, profit: float, time_str: str) -> str:
    message_content = f"{ticker}_{target_price}_{entry_price}_{profit}_{time_str}"
    return hashlib.md5(message_content.encode()).hexdigest()

def is_message_processed(message_id: str) -> bool:
    return message_id in processed_messages

def mark_message_processed(message_id: str):
    processed_messages.add(message_id)

def parse_trim_message(content: str) -> Optional[Match]:
    return config.TRIM_PATTERN.search(content)

def parse_stopped_message(content: str) -> Optional[Match]:
    return config.STOPPED_PATTERN.search(content)

def parse_long_triggered_message(content: str) -> Optional[Match]:
    return config.LONG_TRIGGERED_PATTERN.search(content)

def parse_target_hit_message(content: str) -> Optional[Match]:
    return config.TARGET_HIT_PATTERN.search(content)

def parse_target2_hit_message(content: str) -> Optional[Match]:
    return config.TARGET2_HIT_PATTERN.search(content)

def parse_stop_loss_message(content: str) -> Optional[Match]:
    return config.STOP_LOSS_PATTERN.search(content)

def parse_stop_loss_simple_message(content: str) -> Optional[Match]:
    return config.STOP_LOSS_SIMPLE_PATTERN.search(content)

def parse_es_order_message(content: str) -> Optional[Match]:
    return config.PATTERN.search(content)


class TradingViewEntryResult(TypedDict):
    direction: Literal["long", "short"]
    price: str


class TradingViewExitResult(TypedDict):
    exit_side: Literal["long", "short"]
    price: str


def normalize_tradingview_alert_text(raw: bytes) -> str:
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        s = raw.decode("utf-8", errors="replace")
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s
    if isinstance(obj, dict):
        chunks: list[str] = []
        for key in ("message", "text", "alert", "content", "description"):
            val = obj.get(key)
            if isinstance(val, str):
                chunks.append(val)
        chunks.append(json.dumps(obj, ensure_ascii=False))
        return "\n".join(chunks)
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False)


def _word_to_direction(word: str) -> Literal["long", "short"]:
    u = word.upper()
    if u == "LONG":
        return "long"
    return "short"


def parse_tradingview_arm_direction(text: str) -> Optional[Literal["long", "short"]]:
    m = config.TRADINGVIEW_DTR_ARM_PATTERN.search(text)
    if not m:
        m = config.TRADINGVIEW_TSR_ARM_PATTERN.search(text)
    if not m:
        return None
    return _word_to_direction(m.group(1))


def parse_tradingview_entry(text: str) -> Optional[TradingViewEntryResult]:
    m = config.TRADINGVIEW_NQ_ENTRY_PATTERN.search(text)
    if not m:
        return None
    side_word = m.group(1).upper()
    price = m.group(2)
    if side_word == "LONG":
        direction: Literal["long", "short"] = "long"
    else:
        direction = "short"
    return {"direction": direction, "price": price}


def parse_tradingview_exit(text: str) -> Optional[TradingViewExitResult]:
    m = config.TRADINGVIEW_NQ_EXIT_PATTERN.search(text)
    if not m:
        return None
    exit_word = m.group(1).upper()
    price = m.group(2)
    exit_side: Literal["long", "short"] = "long" if exit_word == "LONG" else "short"
    return {"exit_side": exit_side, "price": price}


def parse_tradingview_stop_loss_hit(text: str) -> Optional[str]:
    m = config.TRADINGVIEW_NQ_STOP_LOSS_PATTERN.search(text)
    if not m:
        return None
    return m.group(1)

