"""Telegram Bot API client — direct HTTP, no dependencies."""
import json
import sys
import urllib.request


def send_message(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        print(f"TG send error: {e}", file=sys.stderr)
        return False
