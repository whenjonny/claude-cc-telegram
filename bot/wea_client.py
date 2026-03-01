"""WEA (Difft OpenAPI) client — HmacSHA256 signed HTTP requests."""
import base64
import hashlib
import hmac
import json
import sys
import time
import urllib.request
import uuid


def build_signature(
    method: str, uri: str, timestamp: str, nonce: str, body: str, app_secret: str,
) -> str:
    string_to_sign = f"{method}\n{uri}\n{timestamp}\n{nonce}\n{body}\n"
    sig = hmac.new(
        app_secret.encode(), string_to_sign.encode(), hashlib.sha256,
    ).digest()
    return base64.b64encode(sig).decode()


def send_message(
    base_url: str, app_id: str, app_secret: str,
    bot_id: str, target_wuid: str, text: str,
) -> bool:
    uri = "/v1/messages"
    url = f"{base_url}{uri}"
    payload = {
        "appId": app_id,
        "botId": bot_id,
        "to": {"wuids": [target_wuid]},
        "msgType": "TEXT",
        "content": {"text": text},
    }
    body = json.dumps(payload)
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    signature = build_signature("POST", uri, timestamp, nonce, body, app_secret)

    req = urllib.request.Request(
        url, data=body.encode(), headers={
            "Content-Type": "application/json",
            "x-difft-appid": app_id,
            "x-difft-sign": signature,
            "x-difft-timestamp": timestamp,
            "x-difft-nonce": nonce,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        print(f"WEA send error: {e}", file=sys.stderr)
        return False
