# WEA Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add WEA (Difft OpenAPI) as a notification channel alongside TG, both notification-only (no buttons/callbacks).

**Architecture:** Hook script `notify.py` reads config `channels` array, dispatches to `tg_client` and/or `wea_client` directly via HTTP. No daemon, no socket. Formatter returns text-only (no buttons).

**Tech Stack:** Python 3, `urllib.request` (stdlib — no new dependencies), `hmac`/`hashlib` for WEA signing.

---

### Task 1: Simplify formatter — remove buttons

**Files:**
- Modify: `bot/formatter.py`
- Modify: `tests/test_formatter.py`

**Step 1: Update tests to expect text-only return**

Replace `tests/test_formatter.py` with:

```python
import pytest
from bot.formatter import format_notification


def test_permission_prompt():
    text = format_notification(
        notification_type="permission_prompt",
        message="Bash: npm install express",
        title="Permission needed",
        session_id="ses1",
        project="my-project",
    )
    assert "my-project" in text
    assert "npm install express" in text


def test_idle_prompt():
    text = format_notification(
        notification_type="idle_prompt",
        message="Claude is idle",
        title="",
        session_id="ses1",
        project="proj",
    )
    assert "waiting" in text.lower() or "idle" in text.lower()


def test_elicitation_dialog():
    text = format_notification(
        notification_type="elicitation_dialog",
        message="Which option?\n1. Option A\n2. Option B",
        title="Choose",
        session_id="ses1",
        project="proj",
    )
    assert "Choose" in text
    assert "Option A" in text


def test_unknown_type():
    text = format_notification(
        notification_type="something_else",
        message="hello",
        title="Title",
        session_id="ses1",
        project="proj",
    )
    assert "hello" in text
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_formatter.py -v`
Expected: FAIL — `format_notification` returns tuple, tests expect str.

**Step 3: Rewrite formatter to return text-only**

Replace `bot/formatter.py` with:

```python
def format_notification(
    notification_type: str,
    message: str,
    title: str,
    session_id: str,
    project: str,
) -> str:
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    header = f"Claude Code [{project}]\nSession: {short_id}"

    if notification_type == "permission_prompt":
        return f"\U0001f514 {header}\n\nPermission needed:\n{message}"
    elif notification_type == "idle_prompt":
        return f"\U0001f4a4 {header}\n\nClaude is idle and waiting for your next instruction."
    elif notification_type == "elicitation_dialog":
        return f"\u2753 {header}\n\n{title}\n{message}"
    else:
        return f"\U0001f514 {header}\n\n{title}\n{message}"
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_formatter.py -v`
Expected: 4 passed.

**Step 5: Commit**

```bash
git add bot/formatter.py tests/test_formatter.py
git commit -m "refactor: simplify formatter to text-only (drop buttons)"
```

---

### Task 2: Create TG client (direct HTTP)

**Files:**
- Create: `bot/tg_client.py`
- Create: `tests/test_tg_client.py`

**Step 1: Write the failing test**

Create `tests/test_tg_client.py`:

```python
import json
from unittest.mock import patch, MagicMock
from bot.tg_client import send_message


def test_send_message_success():
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"ok": True}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("bot.tg_client.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        result = send_message("fake-token", "12345", "Hello")
        assert result is True
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert "sendMessage" in req.full_url
        body = json.loads(req.data)
        assert body["chat_id"] == "12345"
        assert body["text"] == "Hello"


def test_send_message_failure():
    with patch("bot.tg_client.urllib.request.urlopen", side_effect=Exception("network error")):
        result = send_message("fake-token", "12345", "Hello")
        assert result is False
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_tg_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.tg_client'`

**Step 3: Write the implementation**

Create `bot/tg_client.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_tg_client.py -v`
Expected: 2 passed.

**Step 5: Commit**

```bash
git add bot/tg_client.py tests/test_tg_client.py
git commit -m "feat: add TG client (direct HTTP, no daemon)"
```

---

### Task 3: Create WEA client (Difft OpenAPI)

**Files:**
- Create: `bot/wea_client.py`
- Create: `tests/test_wea_client.py`

**Step 1: Write the failing test**

Create `tests/test_wea_client.py`:

```python
import json
from unittest.mock import patch, MagicMock
from bot.wea_client import build_signature, send_message


def test_build_signature():
    sig = build_signature(
        method="POST",
        uri="/v1/messages",
        timestamp="1700000000",
        nonce="test-nonce",
        body='{"test":true}',
        app_secret="secret123",
    )
    assert isinstance(sig, str)
    assert len(sig) > 0  # base64 encoded


def test_build_signature_deterministic():
    args = dict(
        method="POST", uri="/v1/messages", timestamp="1700000000",
        nonce="fixed-nonce", body='{"a":1}', app_secret="key",
    )
    assert build_signature(**args) == build_signature(**args)


def test_send_message_success():
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"data": {"messageId": "123"}}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("bot.wea_client.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        result = send_message(
            base_url="https://openapi.difft.org",
            app_id="app1", app_secret="secret1",
            bot_id="bot1", target_wuid="wuid1",
            text="Hello WEA",
        )
        assert result is True
        req = mock_urlopen.call_args[0][0]
        assert "/v1/messages" in req.full_url
        body = json.loads(req.data)
        assert body["appId"] == "app1"
        assert body["botId"] == "bot1"
        assert body["to"] == {"wuids": ["wuid1"]}
        assert body["msgType"] == "TEXT"
        assert body["content"]["text"] == "Hello WEA"
        assert "x-difft-appid" in req.headers
        assert "X-difft-sign" in req.headers or "x-difft-sign" in {k.lower(): k for k in req.headers}


def test_send_message_failure():
    with patch("bot.wea_client.urllib.request.urlopen", side_effect=Exception("network error")):
        result = send_message(
            base_url="https://openapi.difft.org",
            app_id="a", app_secret="s",
            bot_id="b", target_wuid="w", text="Hi",
        )
        assert result is False
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_wea_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.wea_client'`

**Step 3: Write the implementation**

Create `bot/wea_client.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_wea_client.py -v`
Expected: 4 passed.

**Step 5: Commit**

```bash
git add bot/wea_client.py tests/test_wea_client.py
git commit -m "feat: add WEA client (Difft OpenAPI with HmacSHA256)"
```

---

### Task 4: Create unified notify script + simplify hook_utils

**Files:**
- Create: `scripts/notify.py`
- Modify: `scripts/hook_utils.py`
- Create: `tests/test_notify.py`
- Modify: `tests/test_hooks.py`

**Step 1: Write the failing tests**

Create `tests/test_notify.py`:

```python
import json
from unittest.mock import patch, MagicMock
from scripts.notify import dispatch_notification


def test_dispatch_tg_only():
    config = {
        "channels": ["tg"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=True) as mock_tg:
        result = dispatch_notification(config, "Hello TG")
        mock_tg.assert_called_once_with("tok", "123", "Hello TG")
        assert result is True


def test_dispatch_wea_only():
    config = {
        "channels": ["wea"],
        "wea_app_id": "a",
        "wea_app_secret": "s",
        "wea_bot_id": "b",
        "wea_target_wuid": "w",
        "wea_base_url": "https://openapi.difft.org",
    }
    with patch("scripts.notify.wea_client.send_message", return_value=True) as mock_wea:
        result = dispatch_notification(config, "Hello WEA")
        mock_wea.assert_called_once_with(
            base_url="https://openapi.difft.org",
            app_id="a", app_secret="s",
            bot_id="b", target_wuid="w", text="Hello WEA",
        )
        assert result is True


def test_dispatch_both_channels():
    config = {
        "channels": ["tg", "wea"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
        "wea_app_id": "a", "wea_app_secret": "s",
        "wea_bot_id": "b", "wea_target_wuid": "w",
        "wea_base_url": "https://openapi.difft.org",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=True), \
         patch("scripts.notify.wea_client.send_message", return_value=True):
        result = dispatch_notification(config, "Hello both")
        assert result is True


def test_dispatch_default_channel_when_missing():
    config = {
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=True) as mock_tg:
        result = dispatch_notification(config, "Hello default")
        mock_tg.assert_called_once()
        assert result is True


def test_dispatch_one_fails_other_succeeds():
    config = {
        "channels": ["tg", "wea"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
        "wea_app_id": "a", "wea_app_secret": "s",
        "wea_bot_id": "b", "wea_target_wuid": "w",
        "wea_base_url": "https://openapi.difft.org",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=False), \
         patch("scripts.notify.wea_client.send_message", return_value=True):
        result = dispatch_notification(config, "partial")
        assert result is True
```

Update `tests/test_hooks.py` (remove socket-related test, keep `parse_hook_input`):

```python
import json
import pytest


def test_parse_session_start_input():
    from scripts.hook_utils import parse_hook_input
    raw = json.dumps({
        "session_id": "ses1",
        "cwd": "/proj",
        "hook_event_name": "SessionStart",
    })
    result = parse_hook_input(raw)
    assert result["session_id"] == "ses1"
    assert result["cwd"] == "/proj"


def test_parse_notification_input():
    from scripts.hook_utils import parse_hook_input
    raw = json.dumps({
        "session_id": "ses1",
        "hook_event_name": "Notification",
        "notification_type": "permission_prompt",
        "message": "Bash: ls -la",
        "title": "Permission",
    })
    result = parse_hook_input(raw)
    assert result["notification_type"] == "permission_prompt"
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_notify.py tests/test_hooks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.notify'`

**Step 3: Simplify hook_utils**

Replace `scripts/hook_utils.py` with:

```python
import json
import sys


def parse_hook_input(raw: str) -> dict:
    return json.loads(raw)


def read_stdin() -> dict:
    return parse_hook_input(sys.stdin.read())
```

**Step 4: Create notify.py**

Create `scripts/notify.py`:

```python
#!/usr/bin/env python3
"""Unified notification hook: dispatch to TG and/or WEA channels."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import tg_client, wea_client
from bot.config import load_config
from bot.formatter import format_notification
from scripts.hook_utils import read_stdin


def dispatch_notification(config: dict, text: str) -> bool:
    channels = config.get("channels", ["tg"])
    any_success = False

    for ch in channels:
        if ch == "tg":
            token = config.get("telegram_bot_token")
            chat_id = config.get("telegram_chat_id")
            if token and chat_id:
                if tg_client.send_message(token, chat_id, text):
                    any_success = True

        elif ch == "wea":
            if wea_client.send_message(
                base_url=config.get("wea_base_url", "https://openapi.difft.org"),
                app_id=config.get("wea_app_id", ""),
                app_secret=config.get("wea_app_secret", ""),
                bot_id=config.get("wea_bot_id", ""),
                target_wuid=config.get("wea_target_wuid", ""),
                text=text,
            ):
                any_success = True

    return any_success


def main():
    config = load_config()
    if config is None:
        sys.exit(0)

    data = read_stdin()
    session_id = data.get("session_id", "unknown")
    notification_type = data.get("notification_type", "unknown")
    message = data.get("message", "")
    title = data.get("title", "")
    cwd = data.get("cwd", "")

    project = os.path.basename(cwd) if cwd else "unknown"

    text = format_notification(
        notification_type=notification_type,
        message=message,
        title=title,
        session_id=session_id,
        project=project,
    )

    if dispatch_notification(config, text):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_notify.py tests/test_hooks.py -v`
Expected: 7 passed.

**Step 6: Commit**

```bash
git add scripts/notify.py scripts/hook_utils.py tests/test_notify.py tests/test_hooks.py
git commit -m "feat: unified notify script with multi-channel dispatch"
```

---

### Task 5: Update config, hooks, and clean up old files

**Files:**
- Modify: `config.example.json`
- Modify: `hooks/hooks.json`
- Modify: `.claude/settings.json`
- Delete: `scripts/notify_telegram.py`
- Delete: `scripts/bot_start.py`
- Delete: `scripts/bot_stop.py`

**Step 1: Update config.example.json**

```json
{
  "channels": ["tg"],
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "wea_app_id": "YOUR_APP_ID",
  "wea_app_secret": "YOUR_APP_SECRET",
  "wea_bot_id": "YOUR_BOT_ID",
  "wea_target_wuid": "YOUR_TARGET_WUID",
  "wea_base_url": "https://openapi.difft.org",
  "terminal_mode": "tmux"
}
```

**Step 2: Simplify hooks.json (Notification only)**

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "permission_prompt|idle_prompt|elicitation_dialog",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notify.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Step 3: Update .claude/settings.json**

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "permission_prompt|idle_prompt|elicitation_dialog",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/user/Desktop/claude/claude_wea/scripts/notify.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Step 4: Delete old scripts**

```bash
git rm scripts/notify_telegram.py scripts/bot_start.py scripts/bot_stop.py
```

**Step 5: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All pass. Some old tests that imported deleted modules may need removal — see step 6.

**Step 6: Clean up tests that reference deleted code**

If any tests import from `scripts.notify_telegram`, `scripts.bot_start`, or `scripts.bot_stop`, delete those tests. The `tests/test_integration.py` tests the old socket roundtrip — delete it since we no longer use the socket pipeline.

```bash
git rm tests/test_integration.py
```

**Step 7: Run all tests again**

Run: `python3 -m pytest tests/ -v`
Expected: All remaining tests pass.

**Step 8: Commit**

```bash
git add config.example.json hooks/hooks.json .claude/settings.json
git commit -m "refactor: simplify to notification-only, add WEA config, remove daemon hooks"
```

---

### Task 6: Full verification

**Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass.

**Step 2: Manual TG test**

```bash
python3 -c "
from bot.config import load_config
from bot.tg_client import send_message
c = load_config()
send_message(c['telegram_bot_token'], c['telegram_chat_id'], 'Test from new TG client')
"
```

Expected: Message appears in Telegram.

**Step 3: Manual WEA test (if credentials configured)**

```bash
python3 -c "
from bot.config import load_config
from bot.wea_client import send_message
c = load_config()
send_message(
    base_url=c.get('wea_base_url', 'https://openapi.difft.org'),
    app_id=c['wea_app_id'], app_secret=c['wea_app_secret'],
    bot_id=c['wea_bot_id'], target_wuid=c['wea_target_wuid'],
    text='Test from WEA client',
)
"
```

Expected: Message appears in WEA/企业微信.

**Step 4: Commit any fixes, tag done**

```bash
git log --oneline -5  # verify commit history
```
