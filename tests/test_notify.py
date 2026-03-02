from unittest.mock import patch
from scripts.notify import dispatch_notification

COMMON = dict(session_id="ses1", notification_type="permission_prompt",
              message="Bash: ls", title="Permission", project="proj")


def test_dispatch_tg_via_socket():
    config = {
        "channels": ["tg"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
    }
    with patch("scripts.notify.send_to_bot", return_value=True) as mock_sock:
        result = dispatch_notification(config, **COMMON)
        mock_sock.assert_called_once()
        assert result is True


def test_dispatch_tg_fallback_to_direct():
    config = {
        "channels": ["tg"],
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
    }
    with patch("scripts.notify.send_to_bot", return_value=False), \
         patch("scripts.notify.tg_client.send_message", return_value=True) as mock_tg:
        result = dispatch_notification(config, **COMMON)
        mock_tg.assert_called_once()
        assert result is True


def test_dispatch_wea_only():
    config = {
        "channels": ["wea"],
        "wea_app_id": "a", "wea_app_secret": "s",
        "wea_bot_id": "b", "wea_target_wuid": "w",
        "wea_base_url": "https://openapi.difft.org",
    }
    with patch("scripts.notify.wea_client.send_message", return_value=True) as mock_wea:
        result = dispatch_notification(config, **COMMON)
        mock_wea.assert_called_once()
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
    with patch("scripts.notify.send_to_bot", return_value=True), \
         patch("scripts.notify.wea_client.send_message", return_value=True):
        result = dispatch_notification(config, **COMMON)
        assert result is True


def test_dispatch_default_channel():
    config = {
        "telegram_bot_token": "tok",
        "telegram_chat_id": "123",
    }
    with patch("scripts.notify.send_to_bot", return_value=True) as mock_sock:
        result = dispatch_notification(config, **COMMON)
        mock_sock.assert_called_once()
        assert result is True
