import requests
import time
from typing import Dict, List, Optional, Union
import config

def send_webhook(
    payload: Dict,
    url: str,
    quantity: Optional[int] = None,
    operation_name: str = "webhook"
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
    quantity: Optional[int] = None
):
    if isinstance(urls, str):
        urls = [urls]
    
    if not urls:
        print(f"No URLs provided for {operation_name}")
        return
    
    for url in urls:
        send_webhook(payload, url, quantity, operation_name)

