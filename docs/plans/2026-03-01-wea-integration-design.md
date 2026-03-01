# WEA (Difft OpenAPI) Integration Design

## Goal

Add WEA (企业微信 via Difft OpenAPI) as a notification channel alongside existing Telegram support. Users configure which channels to use via a `channels` array in config.

## Approach: Direct API Calls from Hook Scripts (方案 B)

Replace the daemon-based architecture with direct HTTP calls in the hook script. Both TG and WEA messages are sent directly from the Notification hook — no socket server, no background daemon.

### Trade-offs

- **Removed**: TG inline buttons and remote control. Both channels are notification-only (pure text alerts).
- **Gained**: Simpler architecture, no daemon process, WEA support, more reliable notifications.

## Architecture

```
Claude Code Notification event
  → hooks call: python3 scripts/notify.py
    → reads stdin JSON + loads ~/.claude_wea/config.json
    → for each channel in config.channels:
        "tg"  → tg_client.send_message(text)
        "wea" → wea_client.send_message(text)
    → exit 0 if any channel succeeds
```

## Config Format

```json
{
  "channels": ["tg", "wea"],
  "telegram_bot_token": "BOT_TOKEN",
  "telegram_chat_id": "CHAT_ID",
  "wea_app_id": "APP_ID",
  "wea_app_secret": "APP_SECRET",
  "wea_bot_id": "BOT_ID",
  "wea_target_wuid": "TARGET_WUID",
  "wea_base_url": "https://openapi.difft.org",
  "terminal_mode": "tmux"
}
```

- `channels` defaults to `["tg"]` when absent (backward compatible).
- `wea_base_url` defaults to `https://openapi.difft.org` when absent.

## WEA Client (Difft OpenAPI)

Based on the OpenAPI User Manual (docs/OpenAPI_User_Manual.pdf).

### Authentication

HmacSHA256 signature on each request:

1. Generate nonce (UUID4) and timestamp (epoch seconds).
2. Build string to sign: `{METHOD}\n{URI}\n{TIMESTAMP}\n{NONCE}\n{BODY}\n`
3. Sign with `hmac.new(app_secret, string_to_sign, sha256)`.
4. Base64-encode the signature.
5. Set headers: `x-difft-appid`, `x-difft-sign`, `x-difft-timestamp`, `x-difft-nonce`.

### Send Message

POST `{base_url}/v1/messages`:

```json
{
  "appId": "APP_ID",
  "botId": "BOT_ID",
  "to": {"wuids": ["TARGET_WUID"]},
  "msgType": "TEXT",
  "content": {"text": "notification text"}
}
```

## TG Client (Direct API)

Simple HTTP POST to `https://api.telegram.org/bot{token}/sendMessage` using `urllib.request` (no external dependency). Text-only, no inline buttons.

## File Changes

| File | Change |
|---|---|
| `bot/wea_client.py` | New — Difft OpenAPI sign + send |
| `bot/tg_client.py` | New — direct TG Bot API sendMessage |
| `scripts/notify.py` | New — unified notification dispatcher |
| `scripts/notify_telegram.py` | Delete (replaced by notify.py) |
| `scripts/bot_start.py` | Delete (no daemon auto-start) |
| `scripts/bot_stop.py` | Delete (no daemon auto-stop) |
| `scripts/hook_utils.py` | Simplify (remove socket code) |
| `hooks/hooks.json` | Simplify (Notification only) |
| `.claude/settings.json` | Update hook command |
| `config.example.json` | Add WEA fields + channels |
| `tests/test_wea_client.py` | New |
| `tests/test_tg_client.py` | New |
| `tests/test_notify.py` | New |

## Error Handling

- Each channel sends independently; one failure does not block the other.
- All errors are logged to stderr; hook exits 0 if any channel succeeds.
- Missing config for a channel is silently skipped (e.g., channels includes "wea" but no wea_app_id → skip wea).
