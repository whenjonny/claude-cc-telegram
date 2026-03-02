import json
import os
import socket
import sys

from bot.config import SOCK_FILE


def parse_hook_input(raw: str) -> dict:
    return json.loads(raw)


def read_stdin() -> dict:
    return parse_hook_input(sys.stdin.read())


def build_socket_payload(session_id: str, text: str, buttons: list[dict]) -> bytes:
    return json.dumps({
        "action": "send_notification",
        "session_id": session_id,
        "text": text,
        "buttons": buttons,
    }).encode()


def send_to_bot(payload: bytes) -> bool:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.settimeout(5)
        s.connect(SOCK_FILE)
        s.sendall(payload)
        resp = s.recv(4096)
        result = json.loads(resp.decode())
        return result.get("ok", False)
    except Exception:
        return False
    finally:
        s.close()
