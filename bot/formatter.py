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


import re


def _parse_elicitation_buttons(session_id: str, message: str) -> list[dict]:
    buttons = []
    for line in message.strip().splitlines():
        m = re.match(r'^(\d+)\.\s+(.+)$', line.strip())
        if m:
            buttons.append({"text": m.group(2), "data": f"{session_id}:option_{m.group(1)}"})
    return buttons


def format_tg_notification(
    notification_type: str,
    message: str,
    title: str,
    session_id: str,
    project: str,
) -> tuple[str, list[dict]]:
    text = format_notification(notification_type, message, title, session_id, project)

    if notification_type == "permission_prompt":
        buttons = [
            {"text": "Allow", "data": f"{session_id}:allow"},
            {"text": "Deny", "data": f"{session_id}:deny"},
        ]
    elif notification_type == "elicitation_dialog":
        buttons = _parse_elicitation_buttons(session_id, message)
        if not buttons:
            text += "\n\n-- Type your answer to reply --"
    elif notification_type == "idle_prompt":
        text += "\n\n-- Type to send next instruction --"
        buttons = []
    else:
        buttons = []

    return text, buttons
