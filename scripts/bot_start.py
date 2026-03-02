#!/usr/bin/env python3
"""SessionStart hook: register session and start daemon if needed."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import load_config
from bot.process import is_bot_running
from bot.session import register_session
from scripts.hook_utils import read_stdin

BOT_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot", "tg_bot.py")


def main():
    config = load_config()
    if config is None:
        sys.exit(0)

    data = read_stdin()
    session_id = data.get("session_id", "")
    cwd = data.get("cwd", "")

    # Detect tmux pane
    pane = os.environ.get("TMUX_PANE", "")
    if not pane:
        try:
            pane = subprocess.check_output(
                ["tmux", "display-message", "-p", "#{pane_id}"],
                timeout=3,
            ).decode().strip()
        except Exception:
            pane = ""

    register_session(session_id, pane, cwd)

    if not is_bot_running():
        subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


if __name__ == "__main__":
    main()
