import json
import os
import tempfile
import pytest
from bot.transcript import parse_elicitation_from_transcript


def _write_transcript(lines: list[dict]) -> str:
    """Write JSONL transcript to a temp file, return path."""
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry) + "\n")
    return path


def test_parse_single_question():
    transcript = _write_transcript([
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "AskUserQuestion", "input": {
                "questions": [
                    {
                        "question": "Which library?",
                        "header": "Library",
                        "options": [
                            {"label": "React", "description": "Popular UI framework"},
                            {"label": "Vue", "description": "Progressive framework"},
                        ],
                        "multiSelect": False,
                    }
                ]
            }}
        ]}}
    ])
    try:
        questions = parse_elicitation_from_transcript(transcript)
        assert questions is not None
        assert len(questions) == 1
        assert questions[0]["question"] == "Which library?"
        assert len(questions[0]["options"]) == 2
        assert questions[0]["options"][0]["label"] == "React"
        assert questions[0]["options"][1]["label"] == "Vue"
    finally:
        os.unlink(transcript)


def test_parse_multiple_questions():
    transcript = _write_transcript([
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "AskUserQuestion", "input": {
                "questions": [
                    {
                        "question": "Auth method?",
                        "header": "Auth",
                        "options": [
                            {"label": "JWT", "description": "Token based"},
                            {"label": "OAuth", "description": "Third party"},
                        ],
                        "multiSelect": False,
                    },
                    {
                        "question": "Database?",
                        "header": "DB",
                        "options": [
                            {"label": "PostgreSQL", "description": "Relational"},
                            {"label": "MongoDB", "description": "Document store"},
                        ],
                        "multiSelect": False,
                    },
                ]
            }}
        ]}}
    ])
    try:
        questions = parse_elicitation_from_transcript(transcript)
        assert questions is not None
        assert len(questions) == 2
        assert questions[0]["question"] == "Auth method?"
        assert questions[1]["question"] == "Database?"
    finally:
        os.unlink(transcript)


def test_uses_last_ask():
    """When multiple AskUserQuestion calls exist, use the last one."""
    transcript = _write_transcript([
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "AskUserQuestion", "input": {
                "questions": [{"question": "First?", "header": "Q1",
                               "options": [{"label": "A", "description": ""}], "multiSelect": False}]
            }}
        ]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "AskUserQuestion", "input": {
                "questions": [{"question": "Second?", "header": "Q2",
                               "options": [{"label": "B", "description": ""}], "multiSelect": False}]
            }}
        ]}},
    ])
    try:
        questions = parse_elicitation_from_transcript(transcript)
        assert questions is not None
        assert questions[0]["question"] == "Second?"
    finally:
        os.unlink(transcript)


def test_returns_none_for_missing_file():
    assert parse_elicitation_from_transcript("/nonexistent/path.jsonl") is None


def test_returns_none_for_empty_path():
    assert parse_elicitation_from_transcript("") is None


def test_returns_none_for_no_ask():
    transcript = _write_transcript([
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/foo"}}
        ]}}
    ])
    try:
        assert parse_elicitation_from_transcript(transcript) is None
    finally:
        os.unlink(transcript)


def test_ignores_non_assistant_entries():
    transcript = _write_transcript([
        {"type": "human", "message": {"content": "hello"}},
        {"type": "tool_result", "content": "ok"},
    ])
    try:
        assert parse_elicitation_from_transcript(transcript) is None
    finally:
        os.unlink(transcript)
