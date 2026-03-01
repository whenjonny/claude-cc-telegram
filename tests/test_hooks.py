import json
import pytest


def test_parse_session_start_input():
    from scripts.hook_utils import parse_hook_input
    raw = json.dumps({
        "session_id": "ses1",
        "cwd": "/proj",
        "hook_event_name": "SessionStart",
    })
    result = parse_hook_input(raw)
    assert result["session_id"] == "ses1"
    assert result["cwd"] == "/proj"


def test_parse_notification_input():
    from scripts.hook_utils import parse_hook_input
    raw = json.dumps({
        "session_id": "ses1",
        "hook_event_name": "Notification",
        "notification_type": "permission_prompt",
        "message": "Bash: ls -la",
        "title": "Permission",
    })
    result = parse_hook_input(raw)
    assert result["notification_type"] == "permission_prompt"
