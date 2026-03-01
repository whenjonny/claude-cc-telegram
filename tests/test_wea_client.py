import json
from unittest.mock import patch, MagicMock
from bot.wea_client import build_signature, send_message


def test_build_signature():
    sig = build_signature(
        method="POST",
        uri="/v1/messages",
        timestamp="1700000000",
        nonce="test-nonce",
        body='{"test":true}',
        app_secret="secret123",
    )
    assert isinstance(sig, str)
    assert len(sig) > 0  # base64 encoded


def test_build_signature_deterministic():
    args = dict(
        method="POST", uri="/v1/messages", timestamp="1700000000",
        nonce="fixed-nonce", body='{"a":1}', app_secret="key",
    )
    assert build_signature(**args) == build_signature(**args)


def test_send_message_success():
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"data": {"messageId": "123"}}).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("bot.wea_client.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        result = send_message(
            base_url="https://openapi.difft.org",
            app_id="app1", app_secret="secret1",
            bot_id="bot1", target_wuid="wuid1",
            text="Hello WEA",
        )
        assert result is True
        req = mock_urlopen.call_args[0][0]
        assert "/v1/messages" in req.full_url
        body = json.loads(req.data)
        assert body["appId"] == "app1"
        assert body["botId"] == "bot1"
        assert body["to"] == {"wuids": ["wuid1"]}
        assert body["msgType"] == "TEXT"
        assert body["content"]["text"] == "Hello WEA"
        headers_lower = {k.lower(): v for k, v in req.headers.items()}
        assert "x-difft-appid" in headers_lower
        assert "x-difft-sign" in headers_lower


def test_send_message_failure():
    with patch("bot.wea_client.urllib.request.urlopen", side_effect=Exception("network error")):
        result = send_message(
            base_url="https://openapi.difft.org",
            app_id="a", app_secret="s",
            bot_id="b", target_wuid="w", text="Hi",
        )
        assert result is False
