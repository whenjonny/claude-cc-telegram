import asyncio
import json
import logging
import os
import signal
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
