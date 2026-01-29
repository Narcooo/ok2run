<div align="center">

# 🛡️ ok2run (Agent Approval Gate)

**A self-hosted approval gate for long-running AI agents. Approve from anywhere.**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

[English](README.md) | [中文](README_CN.md)

<img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
<img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"/>

**One approval layer for many agents — when you don't want to auto-allow everything.**

</div>

---

## 😤 The Problem

You're running an AI agent (Claude Code, a long-running bot, or your own) and it needs permission:

```
🤖 Agent wants to run: rm -rf ./build
   Waiting for approval...
```

But you're:
- 🧑‍💼 In a meeting (and don't want to alt-tab into a terminal)
- 🏖️ Trying to stay focused (or procrastinate)
- 🚇 Commuting

**Your agent is stuck. Waiting. Doing nothing.**

---

## 💡 The Solution

<div align="center">

**One-click approval from Telegram or Email. Anywhere.**

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
| 📱 **Remote Approval** | Approve from Telegram or Email, wherever you are |
| ⚡ **One-Click Buttons** | No typing, just tap |
| 🧩 **Policy in One Place** | Centralize allow/deny rules across multiple agents |
| 🏠 **Self-Hosted** | Your data, your server |
| 🐳 **Docker Ready** | `docker compose up -d` and done |

---

## 🚀 Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/Narcooo/ok2run.git
cd ok2run
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
python -m uvicorn agent_approval_gate.main:app --port 8000
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

> **Note:** Commands in `permissions.allow` (in `.claude/settings.local.json`) will bypass the hook and won't be sent to Telegram. To route ALL commands through approval, clear the allow list or remove commands you want to control.

---

### MCP Tools (MCP-compatible clients)

If your agent/client speaks MCP (e.g., Claude Code), you can use the MCP server for explicit approval requests. Otherwise, use the HTTP API section below.

Add to `.mcp.json` (Claude Code):

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

## 🔗 Why This Exists

Long-running agents are only going to get more common. The more autonomy we give them, the more we need a consistent "stop and ask a human" layer for anything with side effects.

ok2run is that layer: a small, self-hosted approval gate with a simple HTTP API. It was inspired by [Moltbot](https://github.com/moltbot/moltbot) and built to be agent-agnostic: plug in any agent, manage approvals in one place.

**Also works great with:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (Anthropic's CLI agent)

---

## 🗺️ Roadmap

### Phase 1: More Channels ✨
- [ ] Slack integration
- [ ] Discord integration
- [ ] WeChat integration
- [ ] Web dashboard

### Phase 2: Full Claude Code Takeover 🚀
- [ ] **Bidirectional Telegram ↔ Claude Code** — not just approvals, but full conversation
- [ ] Send commands to Claude Code from Telegram
- [ ] Receive Claude Code outputs in Telegram
- [ ] Interrupt/pause/resume sessions remotely

### Phase 3: Multi-Agent Management 🤖
- [ ] Dashboard for multiple running agents
- [ ] Unified approval queue
- [ ] Agent status monitoring
- [ ] Approval history & audit logs

---

<div align="center">

**If this saved you from babysitting your AI agent, give it a ⭐**

Made with ☕ so you don't have to babysit terminals

</div>
