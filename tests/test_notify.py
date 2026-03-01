import json
from unittest.mock import patch, MagicMock
from scripts.notify import dispatch_notification


def test_dispatch_tg_only():
    config = {
        "channels": ["tg"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=True) as mock_tg:
        result = dispatch_notification(config, "Hello TG")
        mock_tg.assert_called_once_with("tok", "123", "Hello TG")
        assert result is True


def test_dispatch_wea_only():
    config = {
        "channels": ["wea"],
        "wea_app_id": "a",
        "wea_app_secret": "s",
        "wea_bot_id": "b",
        "wea_target_wuid": "w",
        "wea_base_url": "https://openapi.difft.org",
    }
    with patch("scripts.notify.wea_client.send_message", return_value=True) as mock_wea:
        result = dispatch_notification(config, "Hello WEA")
        mock_wea.assert_called_once_with(
            base_url="https://openapi.difft.org",
            app_id="a", app_secret="s",
            bot_id="b", target_wuid="w", text="Hello WEA",
        )
        assert result is True


def test_dispatch_both_channels():
    config = {
        "channels": ["tg", "wea"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
        "wea_app_id": "a", "wea_app_secret": "s",
        "wea_bot_id": "b", "wea_target_wuid": "w",
        "wea_base_url": "https://openapi.difft.org",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=True), \
         patch("scripts.notify.wea_client.send_message", return_value=True):
        result = dispatch_notification(config, "Hello both")
        assert result is True


def test_dispatch_default_channel_when_missing():
    config = {
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=True) as mock_tg:
        result = dispatch_notification(config, "Hello default")
        mock_tg.assert_called_once()
        assert result is True


def test_dispatch_one_fails_other_succeeds():
    config = {
        "channels": ["tg", "wea"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
        "wea_app_id": "a", "wea_app_secret": "s",
        "wea_bot_id": "b", "wea_target_wuid": "w",
        "wea_base_url": "https://openapi.difft.org",
    }
    with patch("scripts.notify.tg_client.send_message", return_value=False), \
         patch("scripts.notify.wea_client.send_message", return_value=True):
        result = dispatch_notification(config, "partial")
        assert result is True
