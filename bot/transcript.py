"""Parse Claude Code transcript JSONL to extract structured AskUserQuestion data."""
import json
import os


def parse_elicitation_from_transcript(transcript_path: str) -> list[dict] | None:
    """Read the transcript JSONL and extract the last AskUserQuestion's options.

    Returns a list of question dicts like:
        [{"question": "...", "header": "...", "options": [{"label": "...", "description": "..."}], "multiSelect": False}]
    Returns None if not found or on error.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    try:
        # Read from the end to find the most recent AskUserQuestion
        last_ask = None
        with open(transcript_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Look for assistant messages with AskUserQuestion tool_use
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message", {})
                content = message.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if (block.get("type") == "tool_use"
                            and block.get("name") == "AskUserQuestion"):
                        last_ask = block.get("input", {})

        if last_ask is None:
            return None

        questions = last_ask.get("questions", [])
        if not questions:
            return None

        return questions

    except Exception:
        return None
