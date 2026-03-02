import pytest
from bot.formatter import format_notification, format_tg_notification


def test_permission_prompt():
    text = format_notification(
        notification_type="permission_prompt",
        message="Bash: npm install express",
        title="Permission needed",
        session_id="ses1",
        project="my-project",
    )
    assert "my-project" in text
    assert "npm install express" in text


def test_idle_prompt():
    text = format_notification(
        notification_type="idle_prompt",
        message="Claude is idle",
        title="",
        session_id="ses1",
        project="proj",
    )
    assert "waiting" in text.lower() or "idle" in text.lower()


def test_elicitation_dialog():
    text = format_notification(
        notification_type="elicitation_dialog",
        message="Which option?\n1. Option A\n2. Option B",
        title="Choose",
        session_id="ses1",
        project="proj",
    )
    assert "Choose" in text
    assert "Option A" in text


def test_unknown_type():
    text = format_notification(
        notification_type="something_else",
        message="hello",
        title="Title",
        session_id="ses1",
        project="proj",
    )
    assert "hello" in text


def test_tg_permission_buttons():
    text, buttons = format_tg_notification(
        notification_type="permission_prompt",
        message="Bash: rm -rf /",
        title="Permission",
        session_id="ses1",
        project="proj",
    )
    assert "Permission needed" in text
    assert len(buttons) == 2
    assert buttons[0]["text"] == "Allow"
    assert buttons[0]["data"] == "ses1:allow"
    assert buttons[1]["data"] == "ses1:deny"


def test_tg_elicitation_buttons():
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="1. Option A\n2. Option B\n3. Option C",
        title="Choose",
        session_id="ses1",
        project="proj",
    )
    assert "Choose" in text
    assert len(buttons) == 3
    assert buttons[0]["text"] == "Option A"
    assert buttons[0]["data"] == "ses1:option_1"


def test_tg_idle_no_buttons():
    text, buttons = format_tg_notification(
        notification_type="idle_prompt",
        message="",
        title="",
        session_id="ses1",
        project="proj",
    )
    assert "idle" in text.lower() or "waiting" in text.lower()
    assert "Type to send" in text
    assert buttons == []


def test_tg_elicitation_freetext_hint():
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="What is the project name?",
        title="Question",
        session_id="ses1",
        project="proj",
    )
    assert "Type your answer" in text
    assert buttons == []
