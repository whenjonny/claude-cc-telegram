import json
import os
import socket
import sys

SOCK_FILE = os.path.expanduser("~/.claude_wea/bot.sock")


def parse_hook_input(raw: str) -> dict:
    return json.loads(raw)


def read_stdin() -> dict:
    return parse_hook_input(sys.stdin.read())


def build_socket_payload(
    session_id: str,
    notification_type: str,
    text: str,
    buttons: list[dict],
) -> dict:
    return {
        "action": "send_notification",
        "session_id": session_id,
        "notification_type": notification_type,
        "text": text,
        "buttons": buttons,
    }


def send_to_bot(payload: dict) -> dict | None:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(SOCK_FILE)
        sock.sendall(json.dumps(payload).encode())
        response = sock.recv(4096)
        sock.close()
        return json.loads(response.decode())
    except Exception as e:
        print(f"Socket error: {e}", file=sys.stderr)
        return None
