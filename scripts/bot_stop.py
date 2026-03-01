#!/usr/bin/env python3
"""SessionEnd hook: unregister session and stop bot if no sessions remain."""
import json
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
