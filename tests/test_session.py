import json
import os
import pytest
from bot.session import register_session, unregister_session, list_sessions, get_session


def test_register_and_get_session(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    register_session("ses1", tmux_pane="%0", cwd="/proj")
    s = get_session("ses1")
    assert s["session_id"] == "ses1"
    assert s["tmux_pane"] == "%0"
    assert s["cwd"] == "/proj"


def test_unregister_session(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    register_session("ses1", tmux_pane="%0", cwd="/proj")
    unregister_session("ses1")
    assert get_session("ses1") is None


def test_list_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    register_session("ses1", tmux_pane="%0", cwd="/a")
    register_session("ses2", tmux_pane="%1", cwd="/b")
    sessions = list_sessions()
    assert len(sessions) == 2
    ids = {s["session_id"] for s in sessions}
    assert ids == {"ses1", "ses2"}


def test_list_sessions_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    assert list_sessions() == []


def test_unregister_nonexistent(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.session.SESSIONS_DIR", str(tmp_path))
    unregister_session("nope")  # should not raise
