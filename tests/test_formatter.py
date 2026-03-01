import pytest
from bot.formatter import format_notification


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
