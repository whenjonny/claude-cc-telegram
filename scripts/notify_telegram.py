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
