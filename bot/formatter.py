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
