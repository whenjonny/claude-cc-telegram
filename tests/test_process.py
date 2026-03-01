import os
import pytest
from bot.process import is_bot_running, write_pid, read_pid, clear_pid


def test_not_running_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.process.PID_FILE", str(tmp_path / "bot.pid"))
    assert is_bot_running() is False


def test_write_and_read_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(12345)
    assert read_pid() == 12345


def test_is_running_with_current_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(os.getpid())
    assert is_bot_running() is True


def test_is_running_with_dead_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(999999)
    assert is_bot_running() is False


def test_clear_pid(tmp_path, monkeypatch):
    pid_file = str(tmp_path / "bot.pid")
    monkeypatch.setattr("bot.process.PID_FILE", pid_file)
    write_pid(12345)
    clear_pid()
    assert not os.path.exists(pid_file)
