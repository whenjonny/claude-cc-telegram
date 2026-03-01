# Claude WEA - Telegram Remote Control Plugin for Claude Code

**Date:** 2026-03-01
**Status:** Approved

## Goal

When Claude Code pauses and waits for user input (permission prompts, option selections, idle prompts), forward the interaction to Telegram with Inline Keyboard buttons. User responds via TG, and the response is routed back to the correct terminal session.

## Constraints

- No public domain available → cannot use TG webhook, must use long polling
- Must support multiple concurrent Claude Code sessions
- Companion process model: Bot starts/stops with Claude Code lifecycle
- Tech stack: Python + python-telegram-bot
- Delivered as a Claude Code plugin

## Architecture

### Plugin Structure

```
claude-wea/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── remote-control/
│       └── SKILL.md
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── bot_start.py          # SessionStart: register session + start bot if needed
│   ├── bot_stop.py           # SessionEnd: unregister session + stop bot if no sessions
│   └── notify_telegram.py    # Notification: send prompt to bot via socket
├── bot/
│   └── tg_bot.py             # Singleton TG Bot daemon (polling mode)
├── config.example.json
└── requirements.txt
```

### Runtime State Directory

```
~/.claude_wea/
├── config.json               # User config (bot token, chat_id)
├── bot.pid                   # Singleton bot PID
├── bot.sock                  # Unix Domain Socket (bot listens)
└── sessions/
    ├── {session_id}.json     # Per-session registration
    └── ...
```

### Component Interaction

```
Claude Code Session A                    Claude Code Session B
       │                                        │
  [Notification hook]                     [Notification hook]
       │                                        │
  notify_telegram.py                     notify_telegram.py
       │                                        │
       └──────── Unix Socket ───────────────────┘
                      │
                 tg_bot.py (singleton, long polling)
                      │
                 Telegram API
                      │
                 User's Phone
                      │
                 Inline Button Click
                      │
                 tg_bot.py receives callback
                      │
                 Route by session_id in callback_data
                      │
              ┌───────┴───────┐
              ↓               ↓
        tmux send-keys   tmux send-keys
        (Session A pane) (Session B pane)
```

## Hooks Configuration

### hooks.json

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bot_start.py",
            "timeout": 10
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt|idle_prompt|elicitation_dialog",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notify_telegram.py",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bot_stop.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

## Component Details

### 1. bot_start.py (SessionStart hook)

**Input (stdin):** JSON with `session_id`, `cwd`, `hook_event_name`

**Logic:**
1. Read stdin JSON, extract `session_id`
2. Detect tmux pane: `$TMUX_PANE` env var or `tmux display-message -p '#{pane_id}'`
3. Write session file: `~/.claude_wea/sessions/{session_id}.json`
   ```json
   {
     "session_id": "abc123",
     "tmux_pane": "%3",
     "cwd": "/path/to/project",
     "started_at": "2026-03-01T10:00:00Z"
   }
   ```
4. Check if bot is running: read `~/.claude_wea/bot.pid`, verify process alive
5. If not running: spawn `tg_bot.py` as daemon, write PID file
6. Exit 0

### 2. bot_stop.py (SessionEnd hook)

**Input (stdin):** JSON with `session_id`

**Logic:**
1. Read stdin JSON, extract `session_id`
2. Delete `~/.claude_wea/sessions/{session_id}.json`
3. Check if `sessions/` directory is empty
4. If empty: read `bot.pid`, send SIGTERM, delete pid and socket files
5. If not empty: do nothing (other sessions still active)
6. Exit 0

### 3. notify_telegram.py (Notification hook)

**Input (stdin):** JSON with `session_id`, `notification_type`, `message`, `title`

**Logic:**
1. Parse stdin JSON
2. Format message based on `notification_type`:
   - `permission_prompt`: extract tool name and input, create Allow/Deny buttons
   - `idle_prompt`: create "noted" button
   - `elicitation_dialog`: extract options, create corresponding buttons
3. Connect to Unix socket `~/.claude_wea/bot.sock`
4. Send JSON payload:
   ```json
   {
     "action": "send_notification",
     "session_id": "abc123",
     "notification_type": "permission_prompt",
     "title": "Bash command",
     "message": "npm install express",
     "buttons": [
       {"text": "Allow", "data": "allow"},
       {"text": "Deny", "data": "deny"}
     ]
   }
   ```
5. Exit 0

### 4. tg_bot.py (Singleton Bot Daemon)

**Responsibilities:**
- Listen on Unix socket for notifications from hook scripts
- Run TG Bot long polling for Inline button callbacks
- Route callbacks to correct tmux pane

**TG Message Format:**

For `permission_prompt`:
```
🔔 Claude Code [project-name]
Session: abc123

Permission needed:
Bash: npm install express

[✅ Allow]  [❌ Deny]
```

For `idle_prompt`:
```
💤 Claude Code [project-name]
Session: abc123

Claude has finished and is waiting for your next instruction.
```

For `elicitation_dialog`:
```
❓ Claude Code [project-name]
Session: abc123

Which approach do you prefer?

[Option A]  [Option B]  [Option C]
```

**Callback Data Encoding:**
```
{session_id}:{action}
```
Example: `abc123:allow`, `abc123:deny`, `abc123:option_1`

**Callback Handling:**
1. Parse callback_data → extract session_id and action
2. Look up session file → get tmux_pane
3. Map action to terminal input:
   - `allow` → `tmux send-keys -t {pane} 'y' Enter`
   - `deny` → `tmux send-keys -t {pane} 'n' Enter`
   - `option_N` → `tmux send-keys -t {pane} 'N' Enter`
4. Update TG message to show "✅ Responded: Allow" (edit message to confirm)

**Concurrency:**
- Use `asyncio` to handle both socket listener and TG polling in one event loop
- `python-telegram-bot` v20+ is async-native, fits well

### 5. SKILL.md (/claude-wea:remote-control)

Provides manual control:
- No args: show bot status (running/stopped, active sessions)
- `start`: manually start bot
- `stop`: manually stop bot
- `test`: send test message to TG

## Config

`~/.claude_wea/config.json`:
```json
{
  "telegram_bot_token": "123456:ABC-DEF...",
  "telegram_chat_id": "123456789",
  "terminal_mode": "tmux"
}
```

Setup steps:
1. Create TG bot via @BotFather
2. Get chat_id via sending a message and checking getUpdates
3. Fill in config.json

## Error Handling

| Scenario | Behavior |
|---|---|
| Bot process crashes | Next Notification hook detects bot not running, restarts it |
| Socket connection fails | notify_telegram.py logs error, exits non-zero (non-blocking) |
| TG API unreachable | Bot retries with exponential backoff |
| tmux pane no longer exists | Bot logs warning, edits TG message to show "session ended" |
| Config missing | Hook scripts exit 0 silently (don't block Claude Code) |
| Multiple rapid notifications | Bot deduplicates by session_id + timestamp window |

## Dependencies

```
python-telegram-bot>=20.0
```

No other external dependencies. Uses stdlib for: `asyncio`, `json`, `socket`, `subprocess`, `os`, `signal`.
