import re


def format_notification(
    notification_type: str,
    message: str,
    title: str,
    session_id: str,
    project: str,
) -> str:
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    header = f"Claude Code [{project}]\nSession: {short_id}"

    if notification_type == "permission_prompt":
        return f"\U0001f514 {header}\n\nPermission needed:\n{message}"
    elif notification_type == "idle_prompt":
        return f"\U0001f4a4 {header}\n\nClaude is idle and waiting for your next instruction."
    elif notification_type == "elicitation_dialog":
        return f"\u2753 {header}\n\n{title}\n{message}"
    else:
        return f"\U0001f514 {header}\n\n{title}\n{message}"


def _parse_elicitation_buttons(session_id: str, message: str) -> list[dict]:
    buttons = []
    for line in message.strip().splitlines():
        m = re.match(r'^(\d+)\.\s+(.+)$', line.strip())
        if m:
            buttons.append({"text": m.group(2), "data": f"{session_id}:option_{m.group(1)}"})
    return buttons


def _build_buttons_from_questions(session_id: str, questions: list[dict]) -> list[dict]:
    """Build TG inline buttons from structured AskUserQuestion questions data."""
    buttons = []
    for q in questions:
        options = q.get("options", [])
        for i, opt in enumerate(options, 1):
            label = opt.get("label", "")
            desc = opt.get("description", "")
            # Use label as button text, add short desc if label is very short
            if desc and len(label) < 15:
                btn_text = f"{label} - {desc}"
            else:
                btn_text = label
            # Telegram callback_data has 64-byte limit, truncate if needed
            if len(btn_text) > 40:
                btn_text = btn_text[:37] + "..."
            buttons.append({"text": btn_text, "data": f"{session_id}:option_{i}"})
    return buttons


def _format_elicitation_text(
    base_text: str, questions: list[dict]
) -> str:
    """Format elicitation text with structured question details."""
    parts = [base_text]
    for q in questions:
        if q.get("question"):
            parts.append(f"\n{q['question']}")
        options = q.get("options", [])
        for i, opt in enumerate(options, 1):
            line = f"  {i}. {opt.get('label', '')}"
            if opt.get("description"):
                line += f" - {opt['description']}"
            parts.append(line)
    return "\n".join(parts)


def format_tg_notification(
    notification_type: str,
    message: str,
    title: str,
    session_id: str,
    project: str,
    questions: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    text = format_notification(notification_type, message, title, session_id, project)

    if notification_type == "permission_prompt":
        buttons = [
            {"text": "Allow", "data": f"{session_id}:allow"},
            {"text": "Deny", "data": f"{session_id}:deny"},
        ]
    elif notification_type == "elicitation_dialog":
        if questions:
            # Use structured data: better text + accurate buttons
            text = _format_elicitation_text(text, questions)
            buttons = _build_buttons_from_questions(session_id, questions)
        else:
            # Fallback: regex parse from message text
            buttons = _parse_elicitation_buttons(session_id, message)
        if not buttons:
            text += "\n\n-- Type your answer to reply --"
    elif notification_type == "idle_prompt":
        text += "\n\n-- Type to send next instruction --"
        buttons = []
    else:
        buttons = []

    return text, buttons
