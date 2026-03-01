import json
import pytest
from bot.config import load_config, get_session_file


def test_load_config_returns_dict(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.config.STATE_DIR", str(tmp_path))
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "telegram_bot_token": "test-token",
        "telegram_chat_id": "12345",
    }))
    cfg = load_config()
    assert cfg["telegram_bot_token"] == "test-token"
    assert cfg["telegram_chat_id"] == "12345"


def test_load_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.config.STATE_DIR", str(tmp_path))
    cfg = load_config()
    assert cfg is None


def test_get_session_file(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.config.SESSIONS_DIR", str(tmp_path))
    path = get_session_file("abc123")
    assert path == str(tmp_path / "abc123.json")
