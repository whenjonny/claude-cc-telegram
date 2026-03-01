import json
from unittest.mock import patch, MagicMock
from bot.tg_client import send_message


def test_send_message_success():
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"ok": True}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("bot.tg_client.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        result = send_message("fake-token", "12345", "Hello")
        assert result is True
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert "sendMessage" in req.full_url
        body = json.loads(req.data)
        assert body["chat_id"] == "12345"
        assert body["text"] == "Hello"


def test_send_message_failure():
    with patch("bot.tg_client.urllib.request.urlopen", side_effect=Exception("network error")):
        result = send_message("fake-token", "12345", "Hello")
        assert result is False
