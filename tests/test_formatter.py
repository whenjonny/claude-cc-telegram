import pytest
from bot.formatter import format_notification


def test_permission_prompt():
    text, buttons = format_notification(
        notification_type="permission_prompt",
        message="Bash: npm install express",
        title="Permission needed",
        session_id="ses1",
        project="my-project",
    )
    assert "my-project" in text
    assert "npm install express" in text
    assert len(buttons) == 2
    assert buttons[0]["text"] == "Allow"
    assert buttons[0]["data"] == "ses1:allow"
    assert buttons[1]["text"] == "Deny"
    assert buttons[1]["data"] == "ses1:deny"


def test_idle_prompt():
    text, buttons = format_notification(
        notification_type="idle_prompt",
        message="Claude is idle",
        title="",
        session_id="ses1",
        project="proj",
    )
    assert "waiting" in text.lower() or "idle" in text.lower()
    assert len(buttons) == 0


def test_elicitation_dialog():
    text, buttons = format_notification(
        notification_type="elicitation_dialog",
        message="Which option?\n1. Option A\n2. Option B",
        title="Choose",
        session_id="ses1",
        project="proj",
    )
    assert "option" in text.lower()
    assert len(buttons) == 2
    assert buttons[0]["text"] == "Option A"
    assert buttons[0]["data"] == "ses1:option_1"
    assert buttons[1]["text"] == "Option B"
    assert buttons[1]["data"] == "ses1:option_2"


def test_unknown_type():
    text, buttons = format_notification(
        notification_type="something_else",
        message="hello",
        title="Title",
        session_id="ses1",
        project="proj",
    )
    assert "hello" in text
    assert len(buttons) == 0
