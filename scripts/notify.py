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
