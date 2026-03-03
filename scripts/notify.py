#!/usr/bin/env python3
"""Unified notification hook: TG via daemon socket, WEA via direct HTTP."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import tg_client, wea_client
from bot.config import load_config
from bot.formatter import format_notification, format_tg_notification
from bot.transcript import parse_elicitation_from_transcript
from scripts.hook_utils import read_stdin, build_socket_payload, send_to_bot


def dispatch_notification(config: dict, session_id: str,
                          notification_type: str, message: str,
                          title: str, project: str,
                          questions: list[dict] | None = None) -> bool:
    channels = config.get("channels", ["tg"])
    any_success = False

    for ch in channels:
        if ch == "tg":
            token = config.get("telegram_bot_token")
            chat_id = config.get("telegram_chat_id")
            if not (token and chat_id):
                continue
            # Try daemon socket first (supports buttons)
            text, buttons = format_tg_notification(
                notification_type, message, title, session_id, project,
                questions=questions,
            )
            payload = build_socket_payload(session_id, text, buttons)
            if send_to_bot(payload):
                any_success = True
            else:
                # Fallback: direct HTTP (text-only)
                if tg_client.send_message(token, chat_id, text):
                    any_success = True

        elif ch == "wea":
            text = format_notification(
                notification_type, message, title, session_id, project,
            )
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
    transcript_path = data.get("transcript_path", "")

    project = os.path.basename(cwd) if cwd else "unknown"

    # Extract structured options from transcript for elicitation dialogs
    questions = None
    if notification_type == "elicitation_dialog" and transcript_path:
        questions = parse_elicitation_from_transcript(transcript_path)

    if dispatch_notification(config, session_id, notification_type,
                             message, title, project,
                             questions=questions):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
