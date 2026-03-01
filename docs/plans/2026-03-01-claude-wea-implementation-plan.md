# Claude WEA Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Claude Code plugin that forwards interactive prompts to Telegram with Inline Keyboard buttons, enabling remote response from phone.

**Architecture:** Singleton TG Bot daemon communicates with Claude Code hook scripts via Unix Domain Socket. Hooks fire on Notification events, send payloads to the bot, which relays to TG. User clicks Inline buttons, bot routes response back to correct tmux pane via `tmux send-keys`. Session registry with reference counting supports multiple concurrent sessions.

**Tech Stack:** Python 3, python-telegram-bot v20+, asyncio, Unix Domain Socket, tmux

---

### Task 1: Plugin Scaffold + Config

**Files:**
- Create: `claude-wea/.claude-plugin/plugin.json`
- Create: `claude-wea/hooks/hooks.json`
- Create: `claude-wea/config.example.json`
- Create: `claude-wea/requirements.txt`

**Step 1: Create plugin manifest**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "claude-wea",
  "version": "0.1.0",
  "description": "Forward Claude Code interactive prompts to Telegram for remote control"
}
```

**Step 2: Create hooks.json**

Create `hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bot_start.py",
            "timeout": 10
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt|idle_prompt|elicitation_dialog",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notify_telegram.py",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bot_stop.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Step 3: Create config example and requirements**

Create `config.example.json`:

```json
{
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "terminal_mode": "tmux"
}
```

Create `requirements.txt`:

```
python-telegram-bot>=20.0
```

**Step 4: Install dependencies**

Run: `pip3 install python-telegram-bot>=20.0`

**Step 5: Commit scaffold**

```bash
git add .claude-plugin/ hooks/ config.example.json requirements.txt
git commit -m "feat: plugin scaffold with hooks config and dependencies"
```

---

### Task 2: Shared Config + State Utilities

**Files:**
- Create: `claude-wea/bot/config.py`
- Create: `claude-wea/tests/test_config.py`

**Step 1: Write failing test for config loading**

Create `tests/test_config.py`:

```python
import json
import os
import pytest
from bot.config import (
    STATE_DIR,
    SESSIONS_DIR,
    PID_FILE,
    SOCK_FILE,
    load_config,
    get_session_file,
)


def test_load_config_returns_dict(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.config.STATE_DIR", str(tmp_path))
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "telegram_bot_token": "test-token",
        "telegram_chat_id": "12345",
    }))
    cfg = load_config()
    assert cfg["telegram_bot_token"] == "test-token"
    assert cfg["telegram_chat_id"] == "12345"


def test_load_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.config.STATE_DIR", str(tmp_path))
    cfg = load_config()
    assert cfg is None


def test_get_session_file(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.config.SESSIONS_DIR", str(tmp_path))
    path = get_session_file("abc123")
    assert path == str(tmp_path / "abc123.json")
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/user/Desktop/claude/claude_wea && python3 -m pytest tests/test_config.py -v`
Expected: FAIL (module not found)

**Step 3: Implement config module**

Create `bot/__init__.py` (empty) and `bot/config.py`:

```python
import json
import os
from pathlib import Path

STATE_DIR = os.path.expanduser("~/.claude_wea")
SESSIONS_DIR = os.path.join(STATE_DIR, "sessions")
PID_FILE = os.path.join(STATE_DIR, "bot.pid")
SOCK_FILE = os.path.join(STATE_DIR, "bot.sock")
CONFIG_FILE = os.path.join(STATE_DIR, "config.json")


def ensure_dirs():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def load_config():
    config_path = os.path.join(STATE_DIR, "config.json")
    if not os.path.exists(config_path):
        return None
    with open(config_path) as f:
        return json.load(f)


def get_session_file(session_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")
```

Also create `tests/__init__.py` (empty).

**Step 4: Run tests to verify they pass**

Run: `cd /Users/user/Desktop/claude/claude_wea && python3 -m pytest tests/test_config.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add bot/ tests/
git commit -m "feat: config and state directory utilities"
```

---

### Task 3: Session Registry

**Files:**
- Create: `claude-wea/bot/session.py`
- Create: `claude-wea/tests/test_session.py`

**Step 1: Write failing tests**

Create `tests/test_session.py`:

```python
import json
import os
import pytest
from bot.session import register_session, unregister_session, list_sessions, get_session


def test_register_and_get_session(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    register_session("ses1", tmux_pane="%0", cwd="/proj")
    s = get_session("ses1")
    assert s["session_id"] == "ses1"
    assert s["tmux_pane"] == "%0"
    assert s["cwd"] == "/proj"


def test_unregister_session(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    register_session("ses1", tmux_pane="%0", cwd="/proj")
    unregister_session("ses1")
    assert get_session("ses1") is None


def test_list_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    register_session("ses1", tmux_pane="%0", cwd="/a")
    register_session("ses2", tmux_pane="%1", cwd="/b")
    sessions = list_sessions()
    assert len(sessions) == 2
    ids = {s["session_id"] for s in sessions}
    assert ids == {"ses1", "ses2"}


def test_list_sessions_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    assert list_sessions() == []


def test_unregister_nonexistent(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    unregister_session("nope")  # should not raise
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_session.py -v`
Expected: FAIL

**Step 3: Implement session module**

Create `bot/session.py`:

```python
import json
import os
from datetime import datetime, timezone


SESSIONS_DIR = os.path.expanduser("~/.claude_wea/sessions")


def register_session(session_id: str, tmux_pane: str, cwd: str):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    data = {
        "session_id": session_id,
        "tmux_pane": tmux_pane,
        "cwd": cwd,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(path, "w") as f:
        json.dump(data, f)


def unregister_session(session_id: str):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(path):
        os.remove(path)


def get_session(session_id: str):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def list_sessions():
    if not os.path.isdir(SESSIONS_DIR):
        return []
    result = []
    for fname in os.listdir(SESSIONS_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(SESSIONS_DIR, fname)) as f:
                result.append(json.load(f))
    return result
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_session.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add bot/session.py tests/test_session.py
git commit -m "feat: session registry with register/unregister/list"
```

---

### Task 4: Bot Process Manager (PID-based singleton)

**Files:**
- Create: `claude-wea/bot/process.py`
- Create: `claude-wea/tests/test_process.py`

**Step 1: Write failing tests**

Create `tests/test_process.py`:

```python
import os
import signal
import pytest
from bot.process import is_bot_running, write_pid, read_pid, clear_pid


def test_not_running_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.process.PID_FILE", str(tmp_path / "bot.pid"))
    assert is_bot_running() is False


def test_write_and_read_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(12345)
    assert read_pid() == 12345


def test_is_running_with_current_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(os.getpid())  # current process, definitely alive
    assert is_bot_running() is True


def test_is_running_with_dead_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(999999)  # very likely not running
    assert is_bot_running() is False


def test_clear_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(12345)
    clear_pid()
    assert not os.path.exists(pid_file)
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_process.py -v`
Expected: FAIL

**Step 3: Implement process manager**

Create `bot/process.py`:

```python
import os
import signal

PID_FILE = os.path.expanduser("~/.claude_wea/bot.pid")


def write_pid(pid: int):
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def read_pid() -> int | None:
    if not os.path.exists(PID_FILE):
        return None
    with open(PID_FILE) as f:
        try:
            return int(f.read().strip())
        except ValueError:
            return None


def clear_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def is_bot_running() -> bool:
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # signal 0: check if process exists
        return True
    except ProcessLookupError:
        clear_pid()  # stale pid file
        return False
    except PermissionError:
        return True  # process exists but we can't signal it
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_process.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add bot/process.py tests/test_process.py
git commit -m "feat: PID-based singleton bot process manager"
```

---

### Task 5: Message Formatter

**Files:**
- Create: `claude-wea/bot/formatter.py`
- Create: `claude-wea/tests/test_formatter.py`

**Step 1: Write failing tests**

Create `tests/test_formatter.py`:

```python
import pytest
from bot.formatter import format_notification


def test_permission_prompt():
    text, buttons = format_notification(
        notification_type="permission_prompt",
        message="Bash: npm install express",
        title="Permission needed",
        session_id="ses1",
        project="my-project",
    )
    assert "my-project" in text
    assert "npm install express" in text
    assert len(buttons) == 2
    assert buttons[0]["text"] == "Allow"
    assert buttons[0]["data"] == "ses1:allow"
    assert buttons[1]["text"] == "Deny"
    assert buttons[1]["data"] == "ses1:deny"


def test_idle_prompt():
    text, buttons = format_notification(
        notification_type="idle_prompt",
        message="Claude is idle",
        title="",
        session_id="ses1",
        project="proj",
    )
    assert "waiting" in text.lower() or "idle" in text.lower()
    assert len(buttons) == 0  # no actionable buttons for idle


def test_elicitation_dialog():
    text, buttons = format_notification(
        notification_type="elicitation_dialog",
        message="Which option?\n1. Option A\n2. Option B",
        title="Choose",
        session_id="ses1",
        project="proj",
    )
    assert "option" in text.lower()
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_formatter.py -v`
Expected: FAIL

**Step 3: Implement formatter**

Create `bot/formatter.py`:

```python
import os


def format_notification(
    notification_type: str,
    message: str,
    title: str,
    session_id: str,
    project: str,
) -> tuple[str, list[dict]]:
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    header = f"Claude Code [{project}]\nSession: {short_id}"

    if notification_type == "permission_prompt":
        text = f"\U0001f514 {header}\n\nPermission needed:\n{message}"
        buttons = [
            {"text": "Allow", "data": f"{session_id}:allow"},
            {"text": "Deny", "data": f"{session_id}:deny"},
        ]
        return text, buttons

    elif notification_type == "idle_prompt":
        text = f"\U0001f4a4 {header}\n\nClaude is idle and waiting for your next instruction."
        return text, []

    elif notification_type == "elicitation_dialog":
        text = f"\u2753 {header}\n\n{title}\n{message}"
        buttons = _parse_elicitation_buttons(session_id, message)
        return text, buttons

    else:
        text = f"\U0001f514 {header}\n\n{title}\n{message}"
        return text, []


def _parse_elicitation_buttons(session_id: str, message: str) -> list[dict]:
    buttons = []
    for line in message.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Match lines like "1. Option A" or "- Option A"
        for prefix_check in ["1.", "2.", "3.", "4.", "5."]:
            if line.startswith(prefix_check):
                idx = prefix_check[0]
                label = line[len(prefix_check):].strip()
                buttons.append({
                    "text": label[:40],
                    "data": f"{session_id}:option_{idx}",
                })
                break
    return buttons
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_formatter.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add bot/formatter.py tests/test_formatter.py
git commit -m "feat: notification message formatter with inline buttons"
```

---

### Task 6: TG Bot Daemon (tg_bot.py)

**Files:**
- Create: `claude-wea/bot/tg_bot.py`
- Create: `claude-wea/tests/test_tg_bot.py`

This is the core component. It runs two concurrent tasks:
1. Unix socket server (receives notifications from hook scripts)
2. TG Bot polling (receives inline button callbacks)

**Step 1: Write failing test for callback routing**

Create `tests/test_tg_bot.py`:

```python
import pytest
from bot.tg_bot import parse_callback_data, build_tmux_command


def test_parse_callback_allow():
    session_id, action = parse_callback_data("ses1:allow")
    assert session_id == "ses1"
    assert action == "allow"


def test_parse_callback_option():
    session_id, action = parse_callback_data("ses1:option_2")
    assert session_id == "ses1"
    assert action == "option_2"


def test_build_tmux_allow():
    cmd = build_tmux_command("%3", "allow")
    assert cmd == ["tmux", "send-keys", "-t", "%3", "y", "Enter"]


def test_build_tmux_deny():
    cmd = build_tmux_command("%3", "deny")
    assert cmd == ["tmux", "send-keys", "-t", "%3", "n", "Enter"]


def test_build_tmux_option():
    cmd = build_tmux_command("%3", "option_2")
    assert cmd == ["tmux", "send-keys", "-t", "%3", "2", "Enter"]
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_tg_bot.py -v`
Expected: FAIL

**Step 3: Implement tg_bot.py**

Create `bot/tg_bot.py`:

```python
import asyncio
import json
import logging
import os
import signal
import socket
import subprocess
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from bot.config import load_config, SOCK_FILE, PID_FILE
from bot.session import get_session
from bot.process import write_pid, clear_pid

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_callback_data(data: str) -> tuple[str, str]:
    parts = data.split(":", 1)
    return parts[0], parts[1]


def build_tmux_command(pane: str, action: str) -> list[str]:
    if action == "allow":
        key = "y"
    elif action == "deny":
        key = "n"
    elif action.startswith("option_"):
        key = action.split("_", 1)[1]
    else:
        key = action
    return ["tmux", "send-keys", "-t", pane, key, "Enter"]


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    session_id, action = parse_callback_data(query.data)
    session = get_session(session_id)

    if session is None:
        await query.edit_message_text(
            text=query.message.text + "\n\n-- Session ended --"
        )
        return

    pane = session["tmux_pane"]
    cmd = build_tmux_command(pane, action)

    try:
        subprocess.run(cmd, check=True, timeout=5)
        action_label = action.replace("_", " ").title()
        await query.edit_message_text(
            text=query.message.text + f"\n\n-- Responded: {action_label} --"
        )
    except Exception as e:
        logger.error(f"Failed to send keys to tmux: {e}")
        await query.edit_message_text(
            text=query.message.text + f"\n\n-- Error: {e} --"
        )


async def send_tg_message(app: Application, chat_id: str, text: str, buttons: list[dict]):
    keyboard = []
    row = []
    for btn in buttons:
        row.append(InlineKeyboardButton(btn["text"], callback_data=btn["data"]))
        if len(row) >= 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await app.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )


class SocketServer:
    def __init__(self, app: Application, chat_id: str):
        self.app = app
        self.chat_id = chat_id

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await asyncio.wait_for(reader.read(65536), timeout=5)
            if not data:
                return
            payload = json.loads(data.decode())
            if payload.get("action") == "send_notification":
                await send_tg_message(
                    self.app,
                    self.chat_id,
                    payload["text"],
                    payload.get("buttons", []),
                )
                writer.write(b'{"ok":true}')
            elif payload.get("action") == "ping":
                writer.write(b'{"ok":true}')
            else:
                writer.write(b'{"ok":false,"error":"unknown action"}')
        except Exception as e:
            logger.error(f"Socket handler error: {e}")
            writer.write(json.dumps({"ok": False, "error": str(e)}).encode())
        finally:
            await writer.drain()
            writer.close()

    async def start(self):
        if os.path.exists(SOCK_FILE):
            os.remove(SOCK_FILE)
        server = await asyncio.start_unix_server(self.handle_client, path=SOCK_FILE)
        logger.info(f"Socket server listening on {SOCK_FILE}")
        return server


async def run_bot():
    config = load_config()
    if config is None:
        logger.error("No config found at ~/.claude_wea/config.json")
        sys.exit(1)

    token = config["telegram_bot_token"]
    chat_id = config["telegram_chat_id"]

    app = Application.builder().token(token).build()
    app.add_handler(CallbackQueryHandler(handle_callback))

    sock_server = SocketServer(app, chat_id)

    write_pid(os.getpid())

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        clear_pid()
        if os.path.exists(SOCK_FILE):
            os.remove(SOCK_FILE)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    async with app:
        await app.start()
        server = await sock_server.start()
        await app.updater.start_polling()
        logger.info("Bot running. Waiting for events...")

        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await app.updater.stop()
            await app.stop()
            server.close()
            clear_pid()
            if os.path.exists(SOCK_FILE):
                os.remove(SOCK_FILE)


def main():
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_tg_bot.py -v`
Expected: 5 passed (pure function tests, no TG API needed)

**Step 5: Commit**

```bash
git add bot/tg_bot.py tests/test_tg_bot.py
git commit -m "feat: TG bot daemon with socket server and callback routing"
```

---

### Task 7: Hook Scripts (bot_start, bot_stop, notify_telegram)

**Files:**
- Create: `claude-wea/scripts/bot_start.py`
- Create: `claude-wea/scripts/bot_stop.py`
- Create: `claude-wea/scripts/notify_telegram.py`
- Create: `claude-wea/tests/test_hooks.py`

**Step 1: Write failing tests for hook input parsing**

Create `tests/test_hooks.py`:

```python
import json
import pytest


def make_stdin(data: dict) -> str:
    return json.dumps(data)


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


def test_send_to_socket(tmp_path):
    """Test socket client can encode and would send correctly"""
    from scripts.hook_utils import build_socket_payload
    payload = build_socket_payload(
        session_id="ses1",
        notification_type="permission_prompt",
        text="test message",
        buttons=[{"text": "Allow", "data": "ses1:allow"}],
    )
    assert payload["action"] == "send_notification"
    assert payload["text"] == "test message"
    assert len(payload["buttons"]) == 1
```

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_hooks.py -v`
Expected: FAIL

**Step 3: Implement hook_utils**

Create `scripts/__init__.py` (empty) and `scripts/hook_utils.py`:

```python
import json
import os
import socket
import sys

SOCK_FILE = os.path.expanduser("~/.claude_wea/bot.sock")


def parse_hook_input(raw: str) -> dict:
    return json.loads(raw)


def read_stdin() -> dict:
    return parse_hook_input(sys.stdin.read())


def build_socket_payload(
    session_id: str,
    notification_type: str,
    text: str,
    buttons: list[dict],
) -> dict:
    return {
        "action": "send_notification",
        "session_id": session_id,
        "notification_type": notification_type,
        "text": text,
        "buttons": buttons,
    }


def send_to_bot(payload: dict) -> dict | None:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(SOCK_FILE)
        sock.sendall(json.dumps(payload).encode())
        response = sock.recv(4096)
        sock.close()
        return json.loads(response.decode())
    except Exception as e:
        print(f"Socket error: {e}", file=sys.stderr)
        return None
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_hooks.py -v`
Expected: 3 passed

**Step 5: Implement bot_start.py**

Create `scripts/bot_start.py`:

```python
#!/usr/bin/env python3
"""SessionStart hook: register session and start bot if needed."""
import os
import subprocess
import sys

# Add parent dir to path so we can import bot package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import load_config, ensure_dirs
from bot.session import register_session
from bot.process import is_bot_running
from scripts.hook_utils import read_stdin


def main():
    ensure_dirs()

    config = load_config()
    if config is None:
        sys.exit(0)  # no config, silently skip

    data = read_stdin()
    session_id = data.get("session_id", "unknown")
    cwd = data.get("cwd", "")

    # Detect tmux pane
    tmux_pane = os.environ.get("TMUX_PANE", "")
    if not tmux_pane:
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#{pane_id}"],
                capture_output=True, text=True, timeout=3,
            )
            tmux_pane = result.stdout.strip()
        except Exception:
            tmux_pane = ""

    register_session(session_id, tmux_pane=tmux_pane, cwd=cwd)

    if not is_bot_running():
        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bot_script = os.path.join(plugin_root, "bot", "tg_bot.py")
        subprocess.Popen(
            [sys.executable, bot_script],
            start_new_session=True,
            stdout=open(os.path.expanduser("~/.claude_wea/bot.log"), "a"),
            stderr=subprocess.STDOUT,
        )


if __name__ == "__main__":
    main()
```

**Step 6: Implement bot_stop.py**

Create `scripts/bot_stop.py`:

```python
#!/usr/bin/env python3
"""SessionEnd hook: unregister session and stop bot if no sessions remain."""
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.session import unregister_session, list_sessions
from bot.process import read_pid, clear_pid, is_bot_running
from bot.config import SOCK_FILE


def main():
    data_raw = sys.stdin.read()
    if not data_raw.strip():
        sys.exit(0)

    import json
    data = json.loads(data_raw)
    session_id = data.get("session_id", "")

    if session_id:
        unregister_session(session_id)

    remaining = list_sessions()
    if len(remaining) == 0 and is_bot_running():
        pid = read_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            clear_pid()
            if os.path.exists(SOCK_FILE):
                os.remove(SOCK_FILE)


if __name__ == "__main__":
    main()
```

**Step 7: Implement notify_telegram.py**

Create `scripts/notify_telegram.py`:

```python
#!/usr/bin/env python3
"""Notification hook: forward Claude Code prompts to Telegram via bot socket."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.formatter import format_notification
from scripts.hook_utils import read_stdin, build_socket_payload, send_to_bot


def main():
    data = read_stdin()
    session_id = data.get("session_id", "unknown")
    notification_type = data.get("notification_type", "unknown")
    message = data.get("message", "")
    title = data.get("title", "")
    cwd = data.get("cwd", "")

    project = os.path.basename(cwd) if cwd else "unknown"

    text, buttons = format_notification(
        notification_type=notification_type,
        message=message,
        title=title,
        session_id=session_id,
        project=project,
    )

    payload = build_socket_payload(
        session_id=session_id,
        notification_type=notification_type,
        text=text,
        buttons=buttons,
    )

    result = send_to_bot(payload)
    if result and result.get("ok"):
        sys.exit(0)
    else:
        sys.exit(1)  # non-blocking error


if __name__ == "__main__":
    main()
```

**Step 8: Commit**

```bash
git add scripts/ tests/test_hooks.py
git commit -m "feat: hook scripts for session lifecycle and TG notification"
```

---

### Task 8: SKILL.md (remote-control command)

**Files:**
- Create: `claude-wea/skills/remote-control/SKILL.md`

**Step 1: Create skill file**

Create `skills/remote-control/SKILL.md`:

```markdown
---
name: remote-control
description: Manage the Telegram remote control bot for Claude Code notifications
---

Manage the Claude WEA Telegram remote control bot.

Based on the user's request ($ARGUMENTS), do one of:

**No arguments or "status":** Check bot status
- Run: `cat ~/.claude_wea/bot.pid 2>/dev/null && echo "Bot PID: $(cat ~/.claude_wea/bot.pid)" || echo "Bot not running"`
- Run: `ls ~/.claude_wea/sessions/ 2>/dev/null | wc -l` to count active sessions
- Report status to user

**"start":** Manually start the bot
- Run: `python3 ${CLAUDE_PLUGIN_ROOT}/bot/tg_bot.py &`
- Confirm bot started

**"stop":** Manually stop the bot
- Run: `kill $(cat ~/.claude_wea/bot.pid 2>/dev/null) 2>/dev/null; rm -f ~/.claude_wea/bot.pid ~/.claude_wea/bot.sock`
- Confirm bot stopped

**"test":** Send a test message
- Run: `echo '{"action":"ping"}' | python3 -c "import socket,sys,os; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect(os.path.expanduser('~/.claude_wea/bot.sock')); s.sendall(sys.stdin.buffer.read()); print(s.recv(4096).decode()); s.close()"`
- Report result

**"setup":** Guide user through initial setup
- Check if `~/.claude_wea/config.json` exists
- If not, tell user to:
  1. Create a TG bot via @BotFather
  2. Get their chat_id
  3. Create `~/.claude_wea/config.json` with token and chat_id
```

**Step 2: Commit**

```bash
git add skills/
git commit -m "feat: remote-control skill for manual bot management"
```

---

### Task 9: Integration Test + Manual Verification

**Files:**
- Create: `claude-wea/tests/test_integration.py`

**Step 1: Write integration test for socket communication**

Create `tests/test_integration.py`:

```python
import asyncio
import json
import os
import pytest


@pytest.mark.asyncio
async def test_socket_roundtrip(tmp_path):
    """Test that socket server receives and responds to a notification payload."""
    sock_path = str(tmp_path / "test.sock")

    # Minimal mock: just test socket server protocol
    received = []

    async def handler(reader, writer):
        data = await reader.read(65536)
        payload = json.loads(data.decode())
        received.append(payload)
        writer.write(b'{"ok":true}')
        await writer.drain()
        writer.close()

    server = await asyncio.start_unix_server(handler, path=sock_path)

    # Client sends
    reader, writer = await asyncio.open_unix_connection(sock_path)
    payload = {
        "action": "send_notification",
        "session_id": "test",
        "text": "hello",
        "buttons": [],
    }
    writer.write(json.dumps(payload).encode())
    await writer.drain()
    response = await reader.read(4096)
    writer.close()

    assert json.loads(response) == {"ok": True}
    assert len(received) == 1
    assert received[0]["session_id"] == "test"

    server.close()
    await server.wait_closed()
```

**Step 2: Install pytest-asyncio if needed**

Run: `pip3 install pytest-asyncio`

**Step 3: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration test for socket communication"
```

---

### Task 10: Git Init + Final Commit

**Step 1: Initialize git repo**

Run (if not already a git repo):
```bash
cd /Users/user/Desktop/claude/claude_wea
git init
```

**Step 2: Create .gitignore**

Create `.gitignore`:

```
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
.env
config.json
```

**Step 3: Final commit with all files**

```bash
git add .
git commit -m "feat: claude-wea plugin - Telegram remote control for Claude Code"
```

**Step 4: Manual test**

1. Copy `config.example.json` to `~/.claude_wea/config.json` and fill in TG bot token + chat_id
2. Load plugin: `claude --plugin-dir /Users/user/Desktop/claude/claude_wea`
3. Verify SessionStart hook fires and bot starts
4. Trigger a permission prompt and verify TG message arrives
5. Click Inline button and verify response reaches terminal
