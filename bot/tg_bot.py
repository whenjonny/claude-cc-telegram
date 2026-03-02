import asyncio
import json
import logging
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from bot.config import load_config, SOCK_FILE
from bot.session import get_session, list_sessions
from bot.process import write_pid, cleanup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# message_id -> session_id: track which TG message belongs to which session
_msg_session_map: dict[int, str] = {}
# session selected via /list button
_selected_session_id: str | None = None


def _session_label(session: dict) -> str:
    """Human-readable label: folder name + pane id."""
    cwd = session.get("cwd", "")
    name = os.path.basename(cwd) if cwd else "unknown"
    pane = session.get("tmux_pane", "")
    return f"{name} [{pane}]" if pane else name


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


def _send_text_to_pane(pane: str, text: str):
    subprocess.run(["tmux", "send-keys", "-t", pane, "-l", text], check=True, timeout=5)
    subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], check=True, timeout=5)


def _resolve_session(update: Update) -> tuple:
    """Resolve target session from reply or selection. Returns (session, error_msg)."""
    # 1. Reply to a notification message -> use that message's session
    reply = update.message.reply_to_message
    if reply and reply.message_id in _msg_session_map:
        sid = _msg_session_map[reply.message_id]
        session = get_session(sid)
        if session:
            return session, None
        return None, "Session ended."

    # 2. Selected via /list button
    if _selected_session_id:
        session = get_session(_selected_session_id)
        if session:
            return session, None

    # 3. Only one session active -> auto-route
    sessions = list_sessions()
    if len(sessions) == 1:
        return sessions[0], None
    if len(sessions) == 0:
        return None, "No active sessions."

    return None, "Multiple sessions. Reply to a notification or use /list to select."


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    session_id, action = parse_callback_data(query.data)

    # /list selection callback
    if action == "select":
        global _selected_session_id
        _selected_session_id = session_id
        session = get_session(session_id)
        if session:
            await query.edit_message_text(
                text=f"Selected: {_session_label(session)}\nSend text to reply."
            )
        else:
            await query.edit_message_text(text="Session ended.")
        return

    # Normal action callback (allow/deny/option)
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


async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active sessions with selection buttons."""
    sessions = list_sessions()
    if not sessions:
        await update.message.reply_text("No active sessions.")
        return

    keyboard = []
    for s in sessions:
        label = _session_label(s)
        keyboard.append([InlineKeyboardButton(label, callback_data=f"{s['session_id']}:select")])

    await update.message.reply_text(
        "Active sessions:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user text input to target session's tmux pane."""
    text = update.message.text
    session, err = _resolve_session(update)

    if session is None:
        await update.message.reply_text(err)
        return

    pane = session["tmux_pane"]
    try:
        _send_text_to_pane(pane, text)
        await update.message.reply_text(f"Sent to {_session_label(session)}")
    except Exception as e:
        logger.error(f"Failed to send text to tmux: {e}")
        await update.message.reply_text(f"Error: {e}")


async def send_tg_message(app: Application, chat_id: str, text: str,
                          buttons: list[dict], session_id: str = ""):
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
    msg = await app.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )

    # Track message -> session mapping for reply routing
    if session_id:
        _msg_session_map[msg.message_id] = session_id
        # Keep map bounded
        if len(_msg_session_map) > 200:
            oldest = list(_msg_session_map.keys())[:100]
            for k in oldest:
                del _msg_session_map[k]


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
                session_id = payload.get("session_id", "")
                await send_tg_message(
                    self.app,
                    self.chat_id,
                    payload["text"],
                    payload.get("buttons", []),
                    session_id=session_id,
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
    app.add_handler(CommandHandler("list", handle_list))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    sock_server = SocketServer(app, chat_id)

    write_pid(os.getpid())

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        cleanup()
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
            cleanup()


def main():
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
