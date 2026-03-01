import os
import signal

PID_FILE = os.path.expanduser("~/.claude_wea/bot.pid")


def write_pid(pid: int):
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def read_pid() -> int | None:
    if not os.path.exists(PID_FILE):
        return None
    with open(PID_FILE) as f:
        try:
            return int(f.read().strip())
        except ValueError:
            return None


def clear_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def is_bot_running() -> bool:
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        clear_pid()
        return False
    except PermissionError:
        return True
