def format_notification(
    notification_type: str,
    message: str,
    title: str,
    session_id: str,
    project: str,
) -> tuple[str, list[dict]]:
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    header = f"Claude Code [{project}]\nSession: {short_id}"

    if notification_type == "permission_prompt":
        text = f"\U0001f514 {header}\n\nPermission needed:\n{message}"
        buttons = [
            {"text": "Allow", "data": f"{session_id}:allow"},
            {"text": "Deny", "data": f"{session_id}:deny"},
        ]
        return text, buttons

    elif notification_type == "idle_prompt":
        text = f"\U0001f4a4 {header}\n\nClaude is idle and waiting for your next instruction."
        return text, []

    elif notification_type == "elicitation_dialog":
        text = f"\u2753 {header}\n\n{title}\n{message}"
        buttons = _parse_elicitation_buttons(session_id, message)
        return text, buttons

    else:
        text = f"\U0001f514 {header}\n\n{title}\n{message}"
        return text, []


def _parse_elicitation_buttons(session_id: str, message: str) -> list[dict]:
    buttons = []
    for line in message.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        for prefix_check in ["1.", "2.", "3.", "4.", "5."]:
            if line.startswith(prefix_check):
                idx = prefix_check[0]
                label = line[len(prefix_check):].strip()
                buttons.append({
                    "text": label[:40],
                    "data": f"{session_id}:option_{idx}",
                })
                break
    return buttons
