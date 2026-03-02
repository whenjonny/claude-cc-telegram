import json
import os
from datetime import datetime, timezone

from bot.config import SESSIONS_DIR


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
