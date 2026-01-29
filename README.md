<div align="center">

# 🛡️ Agent Approval Gate

**Human-in-the-loop for autonomous AI agents. Approve from anywhere.**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

[English](README.md) | [中文](README_CN.md)

<img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
<img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"/>

**A universal approval protocol for autonomous AI agents that lack built-in permission controls**

</div>

---

## 😤 The Problem

You're running an AI agent (Moltbot, Claude Code, or your own) and it needs permission:

```
🤖 Agent wants to run: rm -rf ./build
   Waiting for approval...
```

But you're:
- 🚶 Away from your desk
- 📱 On your phone
- 🍜 Getting lunch
- 😴 Sleeping while agent works overnight
- 🌍 In a different timezone from your server

**Your agent is stuck. Waiting. Doing nothing.**

---

## 💡 The Solution

<div align="center">

**One-click approval from Telegram. Anywhere.**

```
┌────────────────────────────────────┐
│  🤖 Claude Code wants to run:      │
│                                    │
│  rm -rf ./build                    │
│                                    │
│  ┌────────┐ ┌────────┐ ┌────────┐  │
│  │   ✅   │ │   ❌   │ │   ♾️   │  │
│  │ Approve│ │  Deny  │ │ Always │  │
│  └────────┘ └────────┘ └────────┘  │
└────────────────────────────────────┘
```

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📱 **Remote Approval** | Approve from Telegram or Email, anywhere in the world |
| 🔌 **Universal Protocol** | Simple HTTP API - integrate with any agent via a few lines of code |
| ⚡ **One-Click Buttons** | No typing, just tap |
| 🤖 **Agent Agnostic** | Simple HTTP API - integrate with any autonomous agent |
| 🏠 **Self-Hosted** | Your data, your server |
| 🐳 **Docker Ready** | `docker compose up -d` and done |

---

## 🚀 Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/user/agent-approval-gate.git
cd agent-approval-gate
cp .env.example .env
```

### 2. Get Telegram Bot Token

1. Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the token to `.env`
3. Send `/start` to your new bot
4. Get your chat ID: `https://api.telegram.org/bot<TOKEN>/getUpdates`

### 3. Run

```bash
# Option A: Docker (recommended)
docker compose up -d

# Option B: Local
pip install -e .
python -m uvicorn src.agent_approval_gate.main:app --port 8000
```

### 4. Setup Webhook (for Telegram)

```bash
# If you have a public URL (ngrok, VPS, etc.)
curl -X POST http://localhost:8000/v1/telegram/setup-webhook \
  -H "Authorization: Bearer your-api-key"
```

---

## 🔧 Integration

### Claude Code - Full Takeover ⭐

**Replace ALL permission dialogs with Telegram approval.**

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PermissionRequest": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "APPROVAL_GATE_URL=http://127.0.0.1:8000 APPROVAL_API_KEY=dev-key APPROVAL_TG_CHAT_ID=YOUR_CHAT_ID python3 /path/to/scripts/cc_permission_hook.py",
        "timeout": 300
      }]
    }]
  }
}
```

Now go grab coffee. Your agent will ping you on Telegram. ☕

---

### Claude Code - MCP Tools

For explicit approval requests. Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "approval-gate": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "APPROVAL_GATE_URL": "http://127.0.0.1:8000",
        "APPROVAL_API_KEY": "your-key",
        "APPROVAL_TG_CHAT_ID": "your-chat-id"
      }
    }
  }
}
```

**Available Tools:**

| Tool | What it does |
|------|--------------|
| `execute_approved` | Get approval → Execute command (bypasses dialog) |
| `ask_user` | Ask a question with A/B/C/D options |
| `request_approval` | Request approval, get ID |
| `wait_for_approval` | Wait for user decision |

---

### HTTP API (Any Agent)

For **any autonomous agent** that can make HTTP requests:

```python
# Python example for any agent
import requests

# 1. Request approval
resp = requests.post("http://localhost:8000/v1/approvals",
    headers={"Authorization": "Bearer your-key"},
    json={
        "session_id": "my-agent-session",
        "action_type": "file_delete",
        "title": "Delete build folder",
        "preview": "rm -rf ./build",
        "channel": "telegram",
        "target": {"tg_chat_id": "123456789"}
    })
approval_id = resp.json()["approval_id"]

# 2. Wait for user decision
while True:
    status = requests.get(f"http://localhost:8000/v1/approvals/{approval_id}",
        headers={"Authorization": "Bearer your-key"}).json()
    if status["status"] != "pending":
        break
    time.sleep(2)

# 3. Execute if approved
if status["status"] == "approved":
    os.system("rm -rf ./build")
```

**Or with curl:**

```bash
# Create approval request
curl -X POST http://localhost:8000/v1/approvals \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-agent",
    "action_type": "bash",
    "title": "Delete build folder",
    "preview": "rm -rf ./build",
    "channel": "telegram",
    "target": {"tg_chat_id": "123456789"}
  }'

# Poll for result
curl http://localhost:8000/v1/approvals/appr_xxx \
  -H "Authorization: Bearer your-key"
```

---

## 📱 Approval Buttons

### Standard Mode
| Button | Action |
|--------|--------|
| ✅ Approve | Allow this once |
| ✅ Session | Allow for this session |
| ❌ Deny | Reject |
| ♾️ Always | Always allow this action type |

### Question Mode
| Button | Action |
|--------|--------|
| A / B / C / D | Select option |
| 📝 Custom | Type custom reply |

---

## 🐳 Docker

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

---

## 📝 Environment Variables

```bash
# Required
APPROVAL_API_KEY=your-secret-key
TELEGRAM_BOT_TOKEN=123456:ABC...
APPROVAL_TG_CHAT_ID=your-chat-id

# Optional: Email
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=you@gmail.com
EMAIL_USERNAME=you@gmail.com
EMAIL_PASSWORD=app-password

# Optional: For email one-click buttons
PUBLIC_URL=https://your-domain.com
```

---

## 🤝 Contributing

PRs welcome! Feel free to:
- Add new notification channels (Slack, Discord, WeChat, etc.)
- Improve the UI

---

## 🔗 Why This Exists

Autonomous AI agents like [Moltbot](https://github.com/moltbot/moltbot) are powerful but often lack built-in permission controls. They need to read files, execute commands, and interact with external services - but without human oversight, things can go wrong fast.

This project provides a **standalone approval protocol** that any agent can integrate with via HTTP API.

**Also works great with:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic's CLI agent)

---

## 📄 License

MIT - Do whatever you want.

---

<div align="center">

**If this saved you from babysitting your AI agent, give it a ⭐**

Made with ☕ and frustration from watching terminals

</div>
