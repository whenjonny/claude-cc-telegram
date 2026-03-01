import json
import os

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
