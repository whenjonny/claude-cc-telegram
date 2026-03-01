#!/usr/bin/env python3
"""SessionStart hook: register session and start bot if needed."""
import os
import subprocess
import sys

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
