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


# --- Structured questions tests ---


def test_tg_elicitation_with_structured_questions():
    """When structured questions are provided, use them for buttons."""
    questions = [
        {
            "question": "Which library should we use?",
            "header": "Library",
            "options": [
                {"label": "React", "description": "Popular UI framework"},
                {"label": "Vue", "description": "Progressive framework"},
                {"label": "Svelte", "description": "Compiler-based framework"},
            ],
            "multiSelect": False,
        }
    ]
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="1. React\n2. Vue\n3. Svelte",
        title="Choose",
        session_id="ses1",
        project="proj",
        questions=questions,
    )
    assert len(buttons) == 3
    assert "React" in buttons[0]["text"]
    assert "Popular UI framework" in buttons[0]["text"]
    assert buttons[0]["data"] == "ses1:option_1"
    assert "Vue" in buttons[1]["text"]
    assert buttons[1]["data"] == "ses1:option_2"
    assert "Svelte" in buttons[2]["text"]
    assert buttons[2]["data"] == "ses1:option_3"


def test_tg_elicitation_structured_includes_question_text():
    """Structured questions should include question text in the message."""
    questions = [
        {
            "question": "Which database?",
            "header": "DB",
            "options": [
                {"label": "PostgreSQL", "description": "Relational DB"},
                {"label": "MongoDB", "description": "Document store"},
            ],
            "multiSelect": False,
        }
    ]
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="1. PostgreSQL\n2. MongoDB",
        title="Choose DB",
        session_id="ses1",
        project="proj",
        questions=questions,
    )
    assert "Which database?" in text
    assert "PostgreSQL" in text
    assert "Relational DB" in text


def test_tg_elicitation_structured_long_label_no_desc():
    """Long labels should not get description appended."""
    questions = [
        {
            "question": "Pick one?",
            "header": "Pick",
            "options": [
                {"label": "A very long option label here", "description": "Some desc"},
            ],
            "multiSelect": False,
        }
    ]
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="1. A very long option label here",
        title="Pick",
        session_id="ses1",
        project="proj",
        questions=questions,
    )
    assert len(buttons) == 1
    # Long label (>=15 chars) should use label only
    assert buttons[0]["text"] == "A very long option label here"


def test_tg_elicitation_structured_truncation():
    """Buttons with very long text should be truncated."""
    questions = [
        {
            "question": "Pick?",
            "header": "X",
            "options": [
                {"label": "Short", "description": "A very very very long description that exceeds the limit"},
            ],
            "multiSelect": False,
        }
    ]
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="1. Short",
        title="Pick",
        session_id="ses1",
        project="proj",
        questions=questions,
    )
    assert len(buttons) == 1
    assert len(buttons[0]["text"]) <= 40
    assert buttons[0]["text"].endswith("...")


def test_tg_elicitation_fallback_when_no_questions():
    """When questions is None, fall back to regex parsing."""
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="1. Option A\n2. Option B",
        title="Choose",
        session_id="ses1",
        project="proj",
        questions=None,
    )
    assert len(buttons) == 2
    assert buttons[0]["text"] == "Option A"


def test_tg_elicitation_structured_no_options_shows_hint():
    """Structured questions with no options should show type hint."""
    questions = [
        {
            "question": "What is the name?",
            "header": "Name",
            "options": [],
            "multiSelect": False,
        }
    ]
    text, buttons = format_tg_notification(
        notification_type="elicitation_dialog",
        message="What is the name?",
        title="",
        session_id="ses1",
        project="proj",
        questions=questions,
    )
    assert buttons == []
    assert "Type your answer" in text
