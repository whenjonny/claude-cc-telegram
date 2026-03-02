#!/usr/bin/env python3
"""SessionEnd hook: unregister session and stop daemon if no sessions remain."""
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.process import read_pid, cleanup
from bot.session import unregister_session, list_sessions
from scripts.hook_utils import read_stdin


def main():
    data = read_stdin()
    session_id = data.get("session_id", "")

    unregister_session(session_id)

    if not list_sessions():
        pid = read_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            cleanup()


if __name__ == "__main__":
    main()
