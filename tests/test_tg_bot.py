import pytest
from bot.tg_bot import parse_callback_data, build_tmux_command


def test_parse_callback_allow():
    session_id, action = parse_callback_data("ses1:allow")
    assert session_id == "ses1"
    assert action == "allow"


def test_parse_callback_option():
    session_id, action = parse_callback_data("ses1:option_2")
    assert session_id == "ses1"
    assert action == "option_2"


def test_parse_callback_with_colons_in_session():
    session_id, action = parse_callback_data("ses:with:colons:allow")
    assert session_id == "ses"
    assert action == "with:colons:allow"


def test_build_tmux_allow():
    cmd = build_tmux_command("%3", "allow")
    assert cmd == ["tmux", "send-keys", "-t", "%3", "y", "Enter"]


def test_build_tmux_deny():
    cmd = build_tmux_command("%3", "deny")
    assert cmd == ["tmux", "send-keys", "-t", "%3", "n", "Enter"]


def test_build_tmux_option():
    cmd = build_tmux_command("%3", "option_2")
    assert cmd == ["tmux", "send-keys", "-t", "%3", "2", "Enter"]


def test_build_tmux_unknown_action():
    cmd = build_tmux_command("%3", "custom")
    assert cmd == ["tmux", "send-keys", "-t", "%3", "custom", "Enter"]
