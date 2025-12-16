import requests
import time
from typing import Dict, List, Optional, Union
import config

def send_ntfy_notification(payload: Dict, quantity: Optional[int], operation_name: str):
    try:
        ticker = payload.get("ticker", "Unknown")
        action = payload.get("action", "Unknown")
        price = payload.get("price", "")
        
        qty = quantity if quantity is not None else payload.get("quantity", "Unknown")
        
        title = "Trade Executed"
        message = f"Trade: {ticker} {action} {qty}"
        if price:
            message += f" @ {price}"
        message += f" ({operation_name})"
        
        ntfy_url = "https://ntfy.sh/fcpauldiaz_notifications"
        headers = {
            "Title": title
        }
        
        requests.post(ntfy_url, data=message.encode("utf-8"), headers=headers, timeout=5)
        print(f"ntfy notification sent: {message}")
    except Exception as e:
        print(f"Error sending ntfy notification: {e}")

def send_webhook(
    payload: Dict,
    url: str,
    quantity: Optional[int] = None,
    operation_name: str = "webhook",
    is_entry_trade: bool = False
):
    if not url:
        print(f"No URL provided for {operation_name}")
        return
    
    webhook_payload = payload.copy()
    if quantity is not None:
        webhook_payload["quantity"] = quantity
    elif "quantity" not in webhook_payload:
        webhook_payload["quantity"] = config.GLOBAL_QUANTITY
    
    for attempt in range(5):
        try:
            webhook_response = requests.post(url, json=webhook_payload)
            webhook_response.raise_for_status()
            qty_info = f" (qty: {webhook_payload.get('quantity')})"
            print(f"{operation_name} submitted successfully to {url}{qty_info} (attempt {attempt + 1})")
            if is_entry_trade:
                send_ntfy_notification(webhook_payload, quantity, operation_name)
            break
        except Exception as e:
            print(f"Error submitting {operation_name} to {url} (attempt {attempt + 1}): {e}")
            if attempt < 4:
                time.sleep(1)
            else:
                print(f"{operation_name} failed after all retries for {url}")

def send_webhook_to_multiple_urls(
    payload: Dict,
    urls: Union[List[str], str],
    operation_name: str = "webhook",
    quantity: Optional[int] = None,
    is_entry_trade: bool = False
):
    if isinstance(urls, str):
        urls = [urls]
    
    if not urls:
        print(f"No URLs provided for {operation_name}")
        return
    
    for url in urls:
        send_webhook(payload, url, quantity, operation_name, is_entry_trade)

