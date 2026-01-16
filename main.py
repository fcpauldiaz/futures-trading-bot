import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

import config
import message_parser
import order_executor
import position_tracker

app = FastAPI()

gold_trend: Optional[str] = None

class TakeProfit(BaseModel):
    limitPrice: float

class StopLoss(BaseModel):
    type: str
    stopPrice: float

class OrderPayload(BaseModel):
    ticker: str
    price: float
    action: str
    orderType: str
    quantity: int
    takeProfit: Optional[TakeProfit]
    stopLoss: Optional[StopLoss]

def handle_trim_message(trim_match):
    if not position_tracker.has_open_order():
        print("No open order to trim")
        return
    
    order_info = position_tracker.get_open_order_info()
    if not order_info:
        print("Could not retrieve order info")
        return
    
    numerator = int(trim_match.group(1))
    denominator = int(trim_match.group(2))
    trim_percentage = numerator / denominator
    
    print(f"Trim message: {numerator}/{denominator} = {trim_percentage:.2%}")
    
    original_action = order_info["order_info"]["action"]
    original_quantities = order_info["order_info"]["quantities"]
    
    is_buy = original_action == "buy"
    close_is_buy = not is_buy
    
    personal_close_qty = int(original_quantities["personal"] * trim_percentage)
    webhook_close_qty = int(original_quantities["webhook"] * trim_percentage)
    
    print(f"Closing quantities: Personal={personal_close_qty}, Webhook={webhook_close_qty}")
    
    try:
        if personal_close_qty >= 1:
            print(f"Would submit personal close order: qty={personal_close_qty}, is_buy={close_is_buy}")
        else:
            print(f"Skipping personal close order - quantity is {personal_close_qty} (must be >= 1)")
        
        if webhook_close_qty >= 1:
            webhook_payload = {
                "ticker": config.TICKER_SYMBOL,
                "price": "",
                "action": "sell",
                "orderType": "market"
            }
            
            order_executor.send_webhook(webhook_payload, config.WEBHOOK_URL, webhook_close_qty, "Close webhook")
        else:
            print(f"Skipping webhook submission - quantity is {webhook_close_qty} (must be >= 1)")
        
        if trim_percentage >= 1.0:
            position_tracker.clear_open_order()
            print("Order fully closed and cleared")
        else:
            remaining_quantities = {
                "personal": original_quantities["personal"] - personal_close_qty,
                "webhook": original_quantities["webhook"] - webhook_close_qty
            }
            
            order_info["order_info"]["quantities"] = remaining_quantities
            position_tracker.save_open_order(order_info["order_info"])
            print(f"Order updated with remaining quantities: {remaining_quantities}")
            
            if numerator == 1 and denominator == 8:
                entry_price = order_info["order_info"].get("price")
                remaining_webhook_qty = remaining_quantities.get("webhook", 0)
                if entry_price is None:
                    print("Cannot place stop after 1/8 trim - original entry price not available")
                elif remaining_webhook_qty < 1:
                    print(f"Skipping stop order submission after 1/8 trim - quantity is {remaining_webhook_qty} (must be >= 1)")
                else:
                    stop_price = float(entry_price) - 3.0
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    stop_webhook_payload = {
                        "ticker": config.TICKER_SYMBOL,
                        "action": "sell",
                        "time": current_time,
                        "orderType": "stop",
                        "stopPrice": str(stop_price),
                        "quantityType": "fixed_quantity"
                    }
                    order_executor.send_webhook(stop_webhook_payload, config.WEBHOOK_URL, remaining_webhook_qty, "1/8 trim stop order webhook")
                    print(f"Stop order placed after 1/8 trim at {stop_price} (3 points below entry {entry_price}) for {remaining_webhook_qty} contract(s)")
            
    except Exception as e:
        print(f"Error submitting close orders: {e}")

def handle_stopped_message():
    print("Stopped message received - calling flat and cancel methods")
    
    try:
        print("Would call flatten_and_cancel methods")
        
        if position_tracker.has_open_order():
            position_tracker.clear_open_order()
            print("Open order cleared")
        
        webhook_payload = {
            "ticker": config.TICKER_SYMBOL,
            "action": "exit",
            "orderType": "market",
        }
        
        order_executor.send_webhook(webhook_payload, config.WEBHOOK_URL, config.GLOBAL_QUANTITY, "Stopped webhook")
        
        print("Stopped message handling completed")
        
    except Exception as e:
        print(f"Error handling stopped message: {e}")

def handle_long_triggered_message(triggered_match, source="second_channel"):
    if position_tracker.has_open_order():
        print("Order already open, skipping new order submission")
        return
    
    print(f"Long Triggered message received from {source}")
    
    ticker = config.TICKER_SYMBOL
    interval = int(triggered_match.group(2))
    level = float(triggered_match.group(3))
    score = triggered_match.group(4)
    price = float(triggered_match.group(5))
    time_str = triggered_match.group(6)
    
    print(f"Parsed values: Ticker={ticker}, Interval={interval}, Level={level}, Score={score}, Price={price}, Time={time_str}")
    
    is_buy = True
    order_type = 1
    
    score_parts = score.split('/')
    if len(score_parts) == 2:
        score_value = int(score_parts[0])
        score_max = int(score_parts[1])
        
        if source == "second_channel":
            if score_value < 5:
                print(f"Score {score_value} is below minimum threshold of 5 for second channel, skipping trade")
                return
        else:
            if score_value < 5:
                print(f"Score {score_value} is not greater than 5 for FBD endpoint, skipping trade")
                return
        
        personal_qty = min(15, max(5, score_value * 2))
    else:
        print(f"Invalid score format: {score}, skipping trade")
        return
    
    try:
        result1 = "SIMULATED_ORDER_RESULT"
        print(f"Would submit personal order: qty={personal_qty}, is_buy={is_buy}, order_type={order_type}")
        webhook_qty = config.GLOBAL_QUANTITY
        order_info = {
            "action": "buy",
            "direction": "long",
            "ticker": ticker,
            "interval": interval,
            "level": level,
            "score": score,
            "price": price,
            "time": time_str,
            "order_type": order_type,
            "source": source,
            "quantities": {
                "personal": personal_qty,
                "webhook": webhook_qty
            },
            "results": [
                str(result1) if result1 else None
            ]
        }
        position_tracker.save_open_order(order_info)
        print("Order saved locally")
        
        
        if webhook_qty > 0:
            webhook_payload = {
                "ticker": ticker,
                "price": str(price),
                "action": "buy",
                "orderType": "market"
            }
            
            additional_context = {
                "source": source,
                "direction": "long",
                "score": score,
                "level": level,
                "interval": interval
            }
            
            order_executor.send_webhook(webhook_payload, config.WEBHOOK_URL, webhook_qty, "Long Triggered webhook", is_entry_trade=True, additional_context=additional_context)
        else:
            print(f"Skipping webhook submission - quantity is {webhook_qty} (must be > 0)")
        
    except Exception as e:
        print(f"Error submitting Long Triggered order: {e}")

def handle_target_hit_message(target_match, source="fbd_endpoint"):
    if not position_tracker.has_open_order():
        print("No open order to close for target hit")
        return
    
    print("Target 1 Hit message received - closing position")
    
    ticker = config.TICKER_SYMBOL
    interval = int(target_match.group(2))
    level = float(target_match.group(3))
    target_price = float(target_match.group(4))
    entry_price = float(target_match.group(5))
    profit = float(target_match.group(6))
    time_str = target_match.group(7)
    
    print(f"Parsed target hit values: Ticker={ticker}, Interval={interval}, Level={level}, Target={target_price}, Entry={entry_price}, Profit={profit}, Time={time_str}")

    message_id = message_parser.create_message_id(ticker, target_price, entry_price, profit, time_str)
    
    if message_parser.is_message_processed(message_id):
        return
    
    try:
        order_info = position_tracker.get_open_order_info()
        if not order_info:
            print("Could not retrieve order info for target hit")
            return
        
        order_source = order_info["order_info"].get("source", "unknown")
        if order_source != source:
            print(f"Target 1 hit message ignored - order source is '{order_source}', only processing {source} orders")
            return
        
        original_action = order_info["order_info"]["action"]
        original_quantities = order_info["order_info"]["quantities"]
        
        is_buy = original_action == "buy"
        close_is_buy = not is_buy
        
        webhook_total_qty = original_quantities.get("webhook", 0)
        webhook_close_qty = int(webhook_total_qty / 2)
        remaining_webhook_qty = webhook_total_qty - webhook_close_qty
        
        print(f"Target 1 hit: Closing {webhook_close_qty} of {webhook_total_qty} webhook contracts, remaining: {remaining_webhook_qty}")
        
        if webhook_close_qty >= 1:
            webhook_payload = {
                "ticker": ticker,
                "price": str(target_price),
                "action": "sell",
                "orderType": "market"
            }
            
            order_executor.send_webhook(webhook_payload, config.WEBHOOK_URL, webhook_close_qty, "Target hit close webhook")
        else:
            print(f"Skipping webhook submission - quantity is {webhook_close_qty} (must be >= 1)")
        
        if remaining_webhook_qty >= 1:
            stop_price = entry_price - 3.0
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            
            stop_webhook_payload = {
                "ticker": ticker,
                "action": "sell",
                "time": current_time,
                "orderType": "stop",
                "stopPrice": str(stop_price),
                "quantityType": "fixed_quantity"
            }
            
            order_executor.send_webhook(stop_webhook_payload, config.WEBHOOK_URL, remaining_webhook_qty, "Target hit stop order webhook")
            print(f"Stop order placed at {stop_price} (3 points below entry {entry_price}) for {remaining_webhook_qty} contract(s)")
            
            remaining_quantities = {
                "personal": original_quantities.get("personal", 0),
                "webhook": remaining_webhook_qty
            }
            
            order_info["order_info"]["quantities"] = remaining_quantities
            position_tracker.save_open_order(order_info["order_info"])
            print(f"Order updated with remaining quantities: {remaining_quantities}")
        else:
            print(f"Skipping stop order submission - quantity is {remaining_webhook_qty} (must be >= 1)")
            position_tracker.clear_open_order()
            print("Position fully closed due to target hit")
        
        print(f"Target 1 hit processed. Profit: {profit} pts")
        
        message_parser.mark_message_processed(message_id)
        
    except Exception as e:
        print(f"Error handling target hit message: {e}")

def handle_target2_hit_message(target2_match, source="second_channel"):
    if not position_tracker.has_open_order():
        print("No open order to close for target 2 hit")
        return
    
    print("Target 2 Hit message received - closing remaining position")
    
    ticker = config.TICKER_SYMBOL
    interval = int(target2_match.group(2))
    level = float(target2_match.group(3))
    target_price = float(target2_match.group(4))
    entry_price = float(target2_match.group(5))
    profit = float(target2_match.group(6))
    time_str = target2_match.group(7)
    
    print(f"Parsed target 2 hit values: Ticker={ticker}, Interval={interval}, Level={level}, Target={target_price}, Entry={entry_price}, Profit={profit}, Time={time_str}")
    
    message_id = message_parser.create_message_id(ticker, target_price, entry_price, profit, time_str)
    
    if message_parser.is_message_processed(message_id):
        return
    
    try:
        order_info = position_tracker.get_open_order_info()
        if not order_info:
            print("Could not retrieve order info for target 2 hit")
            return
        
        order_source = order_info["order_info"].get("source", "unknown")
        if order_source != source:
            print(f"Target 2 hit message ignored - order source is '{order_source}', only processing {source} orders")
            return
        
        original_action = order_info["order_info"]["action"]
        original_quantities = order_info["order_info"]["quantities"]
        
        webhook_close_qty = original_quantities.get("webhook", 0)
        
        if webhook_close_qty > 0:
            webhook_payload = {
                "ticker": ticker,
                "price": str(target_price),
                "action": "exit",
                "orderType": "market"
            }
            
            order_executor.send_webhook(webhook_payload, config.WEBHOOK_URL, webhook_close_qty, "Target 2 close webhook")
        else:
            print(f"Skipping webhook submission - quantity is {webhook_close_qty} (must be > 0)")
        
        position_tracker.clear_open_order()
        print(f"Remaining position closed due to target 2 hit. Profit: {profit} pts")
        
        message_parser.mark_message_processed(message_id)
        
    except Exception as e:
        print(f"Error handling target 2 hit message: {e}")

def handle_stop_loss_message(stop_loss_match, source="fbd_endpoint"):
    if not position_tracker.has_open_order():
        print("No open order to close for stop loss hit")
        return
    
    print("Stop Loss Hit message received - closing position")
    
    ticker = config.TICKER_SYMBOL
    interval = int(stop_loss_match.group(2))
    level = float(stop_loss_match.group(3))
    entry_price = float(stop_loss_match.group(4))
    exit_price = float(stop_loss_match.group(5))
    loss = float(stop_loss_match.group(6))
    time_str = stop_loss_match.group(7)
    
    print(f"Parsed stop loss values: Ticker={ticker}, Interval={interval}, Level={level}, Entry={entry_price}, Exit={exit_price}, Loss={loss}, Time={time_str}")
    
    message_id = message_parser.create_message_id(ticker, exit_price, entry_price, loss, time_str)
    
    if message_parser.is_message_processed(message_id):
        print(f"Stop loss message already processed (ID: {message_id}), skipping duplicate")
        return
    
    try:
        order_info = position_tracker.get_open_order_info()
        if not order_info:
            print("Could not retrieve order info for stop loss hit")
            return
        
        order_source = order_info["order_info"].get("source", "unknown")
        if order_source != source:
            print(f"Stop loss message ignored - order source is '{order_source}', only processing {source} orders")
            return
        
        original_action = order_info["order_info"]["action"]
        original_quantities = order_info["order_info"]["quantities"]
        
        webhook_close_qty = original_quantities.get("webhook", 0)
        
        if webhook_close_qty > 0:
            webhook_payload = {
                "ticker": ticker,
                "price": str(exit_price),
                "action": "exit",
                "orderType": "market"
            }
            
            order_executor.send_webhook(webhook_payload, config.WEBHOOK_URL, webhook_close_qty, "Stop loss close webhook")
        else:
            print(f"Skipping webhook submission - quantity is {webhook_close_qty} (must be > 0)")
        
        position_tracker.clear_open_order()
        print(f"Position closed due to stop loss hit. Loss: {loss} pts")
        
        message_parser.mark_message_processed(message_id)
        
    except Exception as e:
        print(f"Error handling stop loss message: {e}")

def handle_stop_loss_simple_message(stop_loss_match, source="second_channel"):
    if not position_tracker.has_open_order():
        print("No open order to close for stop loss hit")
        return
    
    print("Stop Loss message received - closing position")
    
    ticker = config.TICKER_SYMBOL
    interval = int(stop_loss_match.group(2))
    level = float(stop_loss_match.group(3))
    entry_price = float(stop_loss_match.group(4))
    exit_price = float(stop_loss_match.group(5))
    loss = float(stop_loss_match.group(6))
    time_str = datetime.now().isoformat()
    
    print(f"Parsed stop loss values: Ticker={ticker}, Interval={interval}, Level={level}, Entry={entry_price}, Exit={exit_price}, Loss={loss}")
    
    message_id = message_parser.create_message_id(ticker, exit_price, entry_price, loss, time_str)
    
    if message_parser.is_message_processed(message_id):
        return
    
    try:
        order_info = position_tracker.get_open_order_info()
        if not order_info:
            print("Could not retrieve order info for stop loss hit")
            return
        
        order_source = order_info["order_info"].get("source", "unknown")
        if order_source != source:
            print(f"Stop loss message ignored - order source is '{order_source}', only processing {source} orders")
            return
        
        original_action = order_info["order_info"]["action"]
        original_quantities = order_info["order_info"]["quantities"]
        
        webhook_close_qty = original_quantities.get("webhook", 0)
        
        if webhook_close_qty > 0:
            webhook_payload = {
                "ticker": ticker,
                "price": str(exit_price),
                "action": "exit",
                "orderType": "market"
            }
            
            order_executor.send_webhook(webhook_payload, config.WEBHOOK_URL, webhook_close_qty, "Stop loss close webhook")
        else:
            print(f"Skipping webhook submission - quantity is {webhook_close_qty} (must be > 0)")
        
        position_tracker.clear_open_order()
        print(f"Position closed due to stop loss hit. Loss: {loss} pts")
        
        message_parser.mark_message_processed(message_id)
        
    except Exception as e:
        print(f"Error handling stop loss message: {e}")

def is_gold_trend_aligned(action: str, trend: Optional[str]) -> bool:
    if trend is None:
        return True
    
    trend_lower = trend.lower()
    if action == "buy" and trend_lower == "bullish":
        return True
    if action == "sell" and trend_lower == "bearish":
        return True
    return False

def handle_gold_bullish_entry(price: str, target_50: Optional[str] = None):
    if position_tracker.has_gold_order():
        print("Gold order already open, skipping new order submission")
        return True
    
    # global gold_trend
    # if not is_gold_trend_aligned("buy", gold_trend):
    #     print(f"Gold bullish entry skipped - trend mismatch. Current trend: {gold_trend}, requested action: buy")
    #     return False
    
    print(f"Gold bullish entry received with price: {price}")
    
    try:
        order_executor.send_cancel_webhook(config.GOLD_TICKER, config.GOLD_WEBHOOK_URL)
        
        original_action = "buy"
        opposite_action = "sell"
        
        entry_webhook_payload = {
            "ticker": config.GOLD_TICKER,
            "action": original_action,
            "price": price,
            "quantity": str(config.GOLD_QUANTITY),
            "orderType": "market"
        }
        
        additional_context = {
            "source": "gold_webhook",
            "direction": "long"
        }
        
        order_executor.send_webhook_to_multiple_urls(entry_webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold bullish entry webhook", is_entry_trade=True, additional_context=additional_context)
        print(f"Gold bullish entry webhook sent successfully")

        target_50_quantity = str(int(config.GOLD_QUANTITY / 1))
        target_quantity = target_50_quantity
        
        target = None
        if not target_50:
            price_float = float(price)
            target = str(price_float + 14.0)
            print(f"No target provided, setting default target to {target} (entry price + 14 points)")
        
        if target_50:
            target_webhook_payload = {
                "ticker": config.GOLD_TICKER,
                "action": opposite_action,
                "price": target_50,
                "orderType": "limit",
                "quantity": target_quantity
            }
            order_executor.send_webhook_to_multiple_urls(target_webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold target webhook")
            print(f"Gold target webhook sent successfully at price: {target_50} for quantity: {target_quantity}")

        if price:
            price_float = float(price)
            stop_price = price_float - 7.0
            stop_webhook_payload = {
                "ticker": config.GOLD_TICKER,
                "action": opposite_action,
                "orderType": "stop",
                "stopPrice": str(stop_price),
                "quantityType": "fixed_quantity",
                "quantity": str(config.GOLD_QUANTITY)
            }
            order_executor.send_webhook_to_multiple_urls(stop_webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold stop webhook")
            print(f"Gold stop webhook sent successfully at price: {stop_price} (7 points below entry {price})")
            stop = str(stop_price)
        else:
            stop = None
        
        
        order_info = {
            "action": original_action,
            "ticker": config.GOLD_TICKER,
            "price": price,
            "quantity": config.GOLD_QUANTITY
        }
        position_tracker.save_gold_order(order_info)
        print("Gold order saved locally")
        return True
        
    except Exception as e:
        print(f"Error processing gold bullish entry: {e}")
        return False

def handle_gold_bearish_entry(price: str, target_50: Optional[str] = None):
    if position_tracker.has_gold_order():
        print("Gold order already open, skipping new order submission")
        return True
    
    # global gold_trend
    # if not is_gold_trend_aligned("sell", gold_trend):
    #     print(f"Gold bearish entry skipped - trend mismatch. Current trend: {gold_trend}, requested action: sell")
    #     return False
    
    print(f"Gold bearish entry received with price: {price}")
    
    try:
        order_executor.send_cancel_webhook(config.GOLD_TICKER, config.GOLD_WEBHOOK_URL)
        
        original_action = "sell"
        opposite_action = "buy"
        entry_webhook_payload = {
            "ticker": config.GOLD_TICKER,
            "action": original_action,
            "price": price,
            "quantity": str(config.GOLD_QUANTITY),
            "orderType": "market"
        }
        
        additional_context = {
            "source": "gold_webhook",
            "direction": "short"
        }
        
        order_executor.send_webhook_to_multiple_urls(entry_webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold bearish entry webhook", is_entry_trade=True, additional_context=additional_context)
        print(f"Gold bearish entry webhook sent successfully")
        target_50_quantity = str(int(config.GOLD_QUANTITY / 1))
        
        target = None
        if not target_50:
            price_float = float(price)
            target = str(price_float - 14.0)
            print(f"No target provided, setting default target to {target} (entry price - 14 points)")
        
        if target_50:
            target_50_webhook_payload = {
                "ticker": config.GOLD_TICKER,
                "action": opposite_action,
                "price": target_50,
                "orderType": "limit",
                "quantity": target_50_quantity
            }
            order_executor.send_webhook_to_multiple_urls(target_50_webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold target_50 webhook")
        
        if price:
            price_float = float(price)
            stop_price = price_float + 7.0
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            stop_webhook_payload = {
                "ticker": config.GOLD_TICKER,
                "action": opposite_action,
                "time": current_time,
                "orderType": "stop",
                "stopPrice": str(stop_price),
                "quantityType": "fixed_quantity",
                "quantity": str(config.GOLD_QUANTITY)
            }
            order_executor.send_webhook_to_multiple_urls(stop_webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold stop webhook")
            stop = str(stop_price)
        else:
            stop = None
        
        order_info = {
            "action": original_action,
            "ticker": config.GOLD_TICKER,
            "price": price,
            "quantity": config.GOLD_QUANTITY,
            "target_50": target_50,
            "stop": stop
        }
        position_tracker.save_gold_order(order_info)
        print("Gold order saved locally")
        return True
        
    except Exception as e:
        print(f"Error processing gold bearish entry: {e}")
        return False

def handle_gold_50_percent_target(quantity: Optional[str] = None):
    print(f"Gold 50% target hit received")
    
    if not position_tracker.has_gold_order():
        print("No open gold order to close for 50% target hit")
        return
    
    try:
        order_info = position_tracker.get_gold_order_info()
        if not order_info:
            print("Could not retrieve gold order info for 50% target hit")
            return
        
        original_action = order_info["order_info"]["action"]
        opposite_action = "sell" if original_action == "buy" else "buy"
        entry_price = order_info["order_info"]["price"]
        
        target_quantity = quantity if quantity else str(int(config.GOLD_QUANTITY / 2))
        
        webhook_payload = {
            "ticker": config.GOLD_TICKER,
            "action": opposite_action,
            "quantity": target_quantity
        }
        
        order_executor.send_webhook_to_multiple_urls(webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold 50% target hit webhook")
        print(f"Gold 50% target hit webhook sent successfully (opposite action: {opposite_action})")
        
        remaining_quantity = config.GOLD_QUANTITY - int(target_quantity)
        if remaining_quantity > 0:
            order_info["order_info"]["quantity"] = remaining_quantity
            position_tracker.save_gold_order(order_info["order_info"])
            print(f"Gold order updated with remaining quantity: {remaining_quantity}")
            
            stop_price = float(entry_price)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            
            stop_webhook_payload = {
                "ticker": config.GOLD_TICKER,
                "action": opposite_action,
                "time": current_time,
                "orderType": "stop",
                "stopPrice": str(stop_price),
                "quantityType": "fixed_quantity",
                "quantity": str(remaining_quantity)
            }
            
            order_executor.send_webhook_to_multiple_urls(stop_webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold 50% target stop order webhook")
            print(f"Stop order placed at entry price {stop_price} for {remaining_quantity} contract(s)")
        else:
            position_tracker.clear_gold_order()
            print("Gold order cleared after 50% target hit")
        
    except Exception as e:
        print(f"Error processing gold 50% target hit: {e}")

def handle_gold_exit():
    print(f"Gold exit received")
    
    try:
        webhook_payload = {
            "ticker": config.GOLD_TICKER,
            "action": "exit",
            "cancel": "true"
        }
        
        order_executor.send_webhook_to_multiple_urls(webhook_payload, [config.GOLD_WEBHOOK_URL], "Gold exit webhook")
        print(f"Gold exit webhook sent successfully")
        
        position_tracker.clear_gold_order()
        print("Gold order cleared after exit")
        
    except Exception as e:
        print(f"Error processing gold exit: {e}")

def handle_nq_bullish_entry(price: str):
    if position_tracker.has_nq_order():
        print("NQ order already open, skipping new order submission")
        return
    
    print(f"NQ bullish entry received with price: {price}")
    
    try:
        order_executor.send_cancel_webhook(config.NQ_TICKER, config.NQ_WEBHOOK_URL)
        
        original_action = "buy"
        
        entry_webhook_payload = {
            "ticker": config.NQ_TICKER,
            "action": original_action,
            "price": price,
            "quantity": str(config.NQ_QUANTITY),
            "orderType": "market"
        }
        
        additional_context = {
            "source": "nq_webhook",
            "direction": "long"
        }
        
        order_executor.send_webhook_to_multiple_urls(entry_webhook_payload, [config.NQ_WEBHOOK_URL], "NQ bullish entry webhook", is_entry_trade=True, additional_context=additional_context)
        print(f"NQ bullish entry webhook sent successfully")
        
        if price:
            price_float = float(price)
            opposite_action = "sell"
            stop_price = price_float - 7.0
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            stop_webhook_payload = {
                "ticker": config.NQ_TICKER,
                "action": opposite_action,
                "time": current_time,
                "orderType": "stop",
                "stopPrice": str(stop_price),
                "quantityType": "fixed_quantity",
                "quantity": str(config.NQ_QUANTITY)
            }
            order_executor.send_webhook_to_multiple_urls(stop_webhook_payload, [config.NQ_WEBHOOK_URL], "NQ stop webhook")
            print(f"NQ stop webhook sent successfully at price: {stop_price} (7 points below entry {price})")
            stop = str(stop_price)
        else:
            stop = None
        
        order_info = {
            "action": original_action,
            "ticker": config.NQ_TICKER,
            "price": price,
            "quantity": config.NQ_QUANTITY,
            "stop": stop
        }
        position_tracker.save_nq_order(order_info)
        print("NQ order saved locally")
        
    except Exception as e:
        print(f"Error processing NQ bullish entry: {e}")

def handle_nq_bearish_entry(price: str):
    if position_tracker.has_nq_order():
        print("NQ order already open, skipping new order submission")
        return
    
    print(f"NQ bearish entry received with price: {price}")
    
    try:
        order_executor.send_cancel_webhook(config.NQ_TICKER, config.NQ_WEBHOOK_URL)
        
        original_action = "sell"
        
        entry_webhook_payload = {
            "ticker": config.NQ_TICKER,
            "action": original_action,
            "price": price,
            "quantity": str(config.NQ_QUANTITY),
            "orderType": "market"
        }
        
        additional_context = {
            "source": "nq_webhook",
            "direction": "short"
        }
        
        order_executor.send_webhook_to_multiple_urls(entry_webhook_payload, [config.NQ_WEBHOOK_URL], "NQ bearish entry webhook", is_entry_trade=True, additional_context=additional_context)
        print(f"NQ bearish entry webhook sent successfully")
        
        if price:
            price_float = float(price)
            opposite_action = "buy"
            stop_price = price_float + 7.0
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            stop_webhook_payload = {
                "ticker": config.NQ_TICKER,
                "action": opposite_action,
                "time": current_time,
                "orderType": "stop",
                "stopPrice": str(stop_price),
                "quantityType": "fixed_quantity",
                "quantity": str(config.NQ_QUANTITY)
            }
            order_executor.send_webhook_to_multiple_urls(stop_webhook_payload, [config.NQ_WEBHOOK_URL], "NQ stop webhook")
            print(f"NQ stop webhook sent successfully at price: {stop_price} (7 points above entry {price})")
            stop = str(stop_price)
        else:
            stop = None
        
        order_info = {
            "action": original_action,
            "ticker": config.NQ_TICKER,
            "price": price,
            "quantity": config.NQ_QUANTITY,
            "stop": stop
        }
        position_tracker.save_nq_order(order_info)
        print("NQ order saved locally")
        
    except Exception as e:
        print(f"Error processing NQ bearish entry: {e}")

def handle_nq_50_percent_target(quantity: Optional[str] = None):
    print(f"NQ 50% target hit received")
    
    if not position_tracker.has_nq_order():
        print("No open NQ order to close for 50% target hit")
        return
    
    try:
        order_info = position_tracker.get_nq_order_info()
        if not order_info:
            print("Could not retrieve NQ order info for 50% target hit")
            return
        
        original_action = order_info["order_info"]["action"]
        opposite_action = "sell" if original_action == "buy" else "buy"
        entry_price = order_info["order_info"]["price"]
        
        target_quantity = quantity if quantity else str(int(config.NQ_QUANTITY / 2))
        
        webhook_payload = {
            "ticker": config.NQ_TICKER,
            "action": opposite_action,
            "quantity": target_quantity
        }
        
        order_executor.send_webhook_to_multiple_urls(webhook_payload, [config.NQ_WEBHOOK_URL], "NQ 50% target hit webhook")
        print(f"NQ 50% target hit webhook sent successfully (opposite action: {opposite_action})")
        
        remaining_quantity = config.NQ_QUANTITY - int(target_quantity)
        if remaining_quantity > 0:
            order_info["order_info"]["quantity"] = remaining_quantity
            position_tracker.save_nq_order(order_info["order_info"])
            print(f"NQ order updated with remaining quantity: {remaining_quantity}")
            
            stop_price = float(entry_price)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            
            stop_webhook_payload = {
                "ticker": config.NQ_TICKER,
                "action": opposite_action,
                "time": current_time,
                "orderType": "stop",
                "stopPrice": str(stop_price),
                "quantityType": "fixed_quantity",
                "quantity": str(remaining_quantity)
            }
            
            order_executor.send_webhook_to_multiple_urls(stop_webhook_payload, [config.NQ_WEBHOOK_URL], "NQ 50% target stop order webhook")
            print(f"Stop order placed at entry price {stop_price} for {remaining_quantity} contract(s)")
        else:
            position_tracker.clear_nq_order()
            print("NQ order cleared after 50% target hit")
        
    except Exception as e:
        print(f"Error processing NQ 50% target hit: {e}")

def handle_nq_exit():
    print(f"NQ exit received")
    
    try:
        webhook_payload = {
            "ticker": config.NQ_TICKER,
            "action": "exit",
            "cancel": "true"
        }
        
        order_executor.send_webhook_to_multiple_urls(webhook_payload, [config.NQ_WEBHOOK_URL], "NQ exit webhook")
        print(f"NQ exit webhook sent successfully")
        
        position_tracker.clear_nq_order()
        print("NQ order cleared after exit")
        
    except Exception as e:
        print(f"Error processing NQ exit: {e}")

@app.post("/gold-trend")
def handle_gold_trend_webhook(payload: dict):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] Received Gold Trend payload: {json.dumps(payload, indent=2)}")
    
    try:
        trend = payload.get("trend")
        
        if not trend:
            return {
                "status": "error",
                "message": "Trend is required",
                "timestamp": timestamp
            }
        
        trend_lower = trend.lower()
        if trend_lower not in ["bearish", "bullish"]:
            return {
                "status": "error",
                "message": f"Invalid trend value: {trend}. Must be 'bearish' or 'bullish'",
                "timestamp": timestamp
            }
        
        global gold_trend
        gold_trend = trend_lower
        print(f"Gold trend updated to: {gold_trend}")
        
        return {
            "status": "success",
            "message": f"Gold trend set to {gold_trend}",
            "trend": gold_trend,
            "timestamp": timestamp
        }
        
    except Exception as e:
        print(f"Error processing Gold Trend webhook: {e}")
        return {
            "status": "error",
            "message": f"Error processing webhook: {str(e)}",
            "timestamp": timestamp
        }

@app.post("/gold")
def handle_gold_webhook(payload: dict):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] Received Gold payload: {json.dumps(payload, indent=2)}")
    
    try:
        action = payload.get("action")
        
        if not action:
            return {
                "status": "error",
                "message": "Action is required",
                "timestamp": timestamp
            }
        
        if action == "bullish_entry":
            price = payload.get("price")
            if not price:
                return {
                    "status": "error",
                    "message": "Price is required for bullish_entry action",
                    "timestamp": timestamp
                }
            target_50 = payload.get("target_50")
            result = handle_gold_bullish_entry(price, target_50)
            if result is False:
                return {
                    "status": "success",
                    "message": "Gold bullish entry skipped due to trend mismatch",
                    "timestamp": timestamp
                }
            return {
                "status": "success",
                "message": "Gold bullish entry processed successfully",
                "timestamp": timestamp
            }
        
        elif action == "bearish_entry":
            price = payload.get("price")
            if not price:
                return {
                    "status": "error",
                    "message": "Price is required for bearish_entry action",
                    "timestamp": timestamp
                }
            target_50 = payload.get("target_50")
            result = handle_gold_bearish_entry(price, target_50)
            if result is False:
                return {
                    "status": "success",
                    "message": "Gold bearish entry skipped due to trend mismatch",
                    "timestamp": timestamp
                }
            return {
                "status": "success",
                "message": "Gold bearish entry processed successfully",
                "timestamp": timestamp
            }
        
        elif action == "exit":
            handle_gold_exit()
            return {
                "status": "success",
                "message": "Gold exit processed successfully",
                "timestamp": timestamp
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}. Supported actions: bullish_entry, bearish_entry, exit",
                "timestamp": timestamp
            }
            
    except Exception as e:
        print(f"Error processing Gold webhook: {e}")
        return {
            "status": "error",
            "message": f"Error processing webhook: {str(e)}",
            "timestamp": timestamp
        }

@app.post("/nq")
def handle_nq_webhook(payload: dict):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] Received NQ payload: {json.dumps(payload, indent=2)}")
    
    try:
        action = payload.get("action")
        
        if not action:
            return {
                "status": "error",
                "message": "Action is required",
                "timestamp": timestamp
            }
        
        if action == "bullish_entry":
            price = payload.get("price")
            if not price:
                return {
                    "status": "error",
                    "message": "Price is required for bullish_entry action",
                    "timestamp": timestamp
                }
            handle_nq_bullish_entry(price)
            return {
                "status": "success",
                "message": "NQ bullish entry processed successfully",
                "timestamp": timestamp
            }
        
        elif action == "bearish_entry":
            price = payload.get("price")
            if not price:
                return {
                    "status": "error",
                    "message": "Price is required for bearish_entry action",
                    "timestamp": timestamp
                }
            handle_nq_bearish_entry(price)
            return {
                "status": "success",
                "message": "NQ bearish entry processed successfully",
                "timestamp": timestamp
            }
        
        elif action == "exit":
            handle_nq_exit()
            return {
                "status": "success",
                "message": "NQ exit processed successfully",
                "timestamp": timestamp
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}. Supported actions: bullish_entry, bearish_entry, exit",
                "timestamp": timestamp
            }
            
    except Exception as e:
        print(f"Error processing NQ webhook: {e}")
        return {
            "status": "error",
            "message": f"Error processing webhook: {str(e)}",
            "timestamp": timestamp
        }

@app.post("/fbd")
def handle_fbd_webhook(payload: dict):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] Received FBD payload: {json.dumps(payload, indent=2)}")
    
    try:
        embeds = payload.get("embeds", [])
        if not embeds or len(embeds) == 0:
            print("No embeds found in payload")
            return {"status": "error", "message": "No embeds found in payload"}
        
        embed_content = embeds[0].get("description", "")
        if not embed_content:
            print("No description found in embed")
            return {"status": "error", "message": "No description found in embed"}
        
        print(f"Processing embed description: {embed_content}")
        
        target_hit_match = message_parser.parse_target_hit_message(embed_content)
        if target_hit_match:
            print("Target 1 Hit message found in FBD webhook")
            handle_target_hit_message(target_hit_match, source="fbd_endpoint")
            return {
                "status": "success", 
                "message": "Target 1 Hit message processed successfully",
                "timestamp": timestamp
            }
        
        target2_hit_match = message_parser.parse_target2_hit_message(embed_content)
        if target2_hit_match:
            print("Target 2 Hit message found in FBD webhook")
            handle_target2_hit_message(target2_hit_match, source="fbd_endpoint")
            return {
                "status": "success", 
                "message": "Target 2 Hit message processed successfully",
                "timestamp": timestamp
            }
        
        stop_loss_match = message_parser.parse_stop_loss_message(embed_content)
        if stop_loss_match:
            print("Stop Loss Hit message found in FBD webhook")
            handle_stop_loss_message(stop_loss_match, source="fbd_endpoint")
            return {
                "status": "success", 
                "message": "Stop Loss Hit message processed successfully",
                "timestamp": timestamp
            }
        
        triggered_match = message_parser.parse_long_triggered_message(embed_content)
        if triggered_match:
            print("Long Triggered message found in FBD webhook " + datetime.now().isoformat())
            handle_long_triggered_message(triggered_match, source="fbd_endpoint")
            return {
                "status": "success", 
                "message": "Long Triggered message processed successfully",
                "timestamp": timestamp
            }
        else:
            print("No Long Triggered, Target 1, Target 2, or Stop Loss pattern matched in embed description")
            return {
                "status": "info", 
                "message": "No Long Triggered, Target 1, Target 2, or Stop Loss pattern matched",
                "timestamp": timestamp
            }
            
    except Exception as e:
        print(f"Error processing FBD webhook: {e}")
        return {
            "status": "error", 
            "message": f"Error processing webhook: {str(e)}",
            "timestamp": timestamp
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

