---
name: remote-control
description: Manage the Telegram remote control bot for Claude Code notifications
---

Manage the Claude WEA Telegram remote control bot.

Based on the user's request ($ARGUMENTS), do one of:

**No arguments or "status":** Check bot status
- Run: `cat ~/.claude_wea/bot.pid 2>/dev/null && echo "Bot PID: $(cat ~/.claude_wea/bot.pid)" || echo "Bot not running"`
- Run: `ls ~/.claude_wea/sessions/ 2>/dev/null | wc -l` to count active sessions
- Report status to user

**"start":** Manually start the bot
- Run: `python3 ${CLAUDE_PLUGIN_ROOT}/bot/tg_bot.py &`
- Confirm bot started

**"stop":** Manually stop the bot
- Run: `kill $(cat ~/.claude_wea/bot.pid 2>/dev/null) 2>/dev/null; rm -f ~/.claude_wea/bot.pid ~/.claude_wea/bot.sock`
- Confirm bot stopped

**"test":** Send a test message to verify connectivity
- Run: `echo '{"action":"ping"}' | python3 -c "import socket,sys,os; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect(os.path.expanduser('~/.claude_wea/bot.sock')); s.sendall(sys.stdin.buffer.read()); print(s.recv(4096).decode()); s.close()"`
- Report result

**"setup":** Guide user through initial setup
- Check if `~/.claude_wea/config.json` exists
- If not, tell user to:
  1. Create a TG bot via @BotFather, get the bot token
  2. Send any message to the bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find the chat_id
  3. Create `~/.claude_wea/config.json`:
     ```json
     {
       "telegram_bot_token": "YOUR_BOT_TOKEN",
       "telegram_chat_id": "YOUR_CHAT_ID",
       "terminal_mode": "tmux"
     }
     ```
  4. Ensure tmux is running
  5. Load plugin: `claude --plugin-dir /path/to/claude-wea`
