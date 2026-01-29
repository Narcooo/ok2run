<div align="center">

# 🛡️ Agent Approval Gate

**自主 AI Agent 的人工审批协议。随时随地批准。**

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

[English](README.md) | 中文

<img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
<img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"/>

**为缺乏内置权限控制的自主 AI Agent 提供通用审批协议**

</div>

---

## 😤 问题

你在运行一个 AI Agent（Moltbot、Claude Code 或自己开发的），它需要权限：

```
🤖 Agent 想要执行: rm -rf ./build
   等待审批中...
```

但你：
- 🚶 不在电脑前
- 📱 在用手机
- 🍜 出去吃饭了
- 😴 让 Agent 通宵工作
- 🌍 和服务器不在同一时区

**你的 Agent 卡住了。等着。什么都做不了。**

---

## 💡 解决方案

<div align="center">

**Telegram 一键审批。随时随地。**

```
┌────────────────────────────────────┐
│  🤖 Claude Code 想要执行:          │
│                                    │
│  rm -rf ./build                    │
│                                    │
│  ┌────────┐ ┌────────┐ ┌────────┐  │
│  │   ✅   │ │   ❌   │ │   ♾️   │  │
│  │  批准  │ │  拒绝  │ │  永久  │  │
│  └────────┘ └────────┘ └────────┘  │
└────────────────────────────────────┘
```

</div>

---

## ✨ 特性

| 特性 | 描述 |
|------|------|
| 📱 **远程审批** | 通过 Telegram 或 Email，在世界任何地方审批 |
| 🔌 **通用协议** | 简单的 HTTP API - 几行代码即可集成任何 Agent |
| ⚡ **一键按钮** | 不用打字，点一下就行 |
| 🤖 **Agent 无关** | 简单的 HTTP API - 可集成任何自主 Agent |
| 🏠 **自托管** | 你的数据，你的服务器 |
| 🐳 **Docker 就绪** | `docker compose up -d` 搞定 |

---

## 🚀 快速开始

### 1. 克隆 & 配置

```bash
git clone https://github.com/user/agent-approval-gate.git
cd agent-approval-gate
cp .env.example .env
```

### 2. 获取 Telegram Bot Token

1. 给 [@BotFather](https://t.me/BotFather) 发消息 → `/newbot`
2. 把 token 复制到 `.env`
3. 给你的新机器人发送 `/start`
4. 获取 chat ID: `https://api.telegram.org/bot<TOKEN>/getUpdates`

### 3. 运行

```bash
# 方式 A: Docker（推荐）
docker compose up -d

# 方式 B: 本地运行
pip install -e .
python -m uvicorn src.agent_approval_gate.main:app --port 8000
```

### 4. 设置 Webhook（Telegram）

```bash
# 如果你有公网 URL（ngrok、VPS 等）
curl -X POST http://localhost:8000/v1/telegram/setup-webhook \
  -H "Authorization: Bearer your-api-key"
```

---

## 🔧 集成方式

### Claude Code - 完全接管 ⭐

**用 Telegram 审批替换所有权限对话框。**

添加到 `~/.claude/settings.json`：

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

现在去喝杯咖啡吧。Agent 会在 Telegram 上找你。☕

> **注意：** `.claude/settings.local.json` 中 `permissions.allow` 里的命令会绕过 hook，不会发送到 Telegram。如果想让所有命令都走审批，需要清空 allow 列表或移除你想控制的命令。

---

### Claude Code - MCP 工具

用于显式审批请求。添加到 `.mcp.json`：

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

**可用工具：**

| 工具 | 功能 |
|------|------|
| `execute_approved` | 获取审批 → 执行命令（绕过对话框） |
| `ask_user` | 向用户提问（A/B/C/D 选项） |
| `request_approval` | 请求审批，获取 ID |
| `wait_for_approval` | 等待用户决定 |

---

### HTTP API（任意 Agent）

适用于**任何能发 HTTP 请求的自主 Agent**：

```python
# Python 示例
import requests

# 1. 请求审批
resp = requests.post("http://localhost:8000/v1/approvals",
    headers={"Authorization": "Bearer your-key"},
    json={
        "session_id": "my-agent-session",
        "action_type": "file_delete",
        "title": "删除 build 文件夹",
        "preview": "rm -rf ./build",
        "channel": "telegram",
        "target": {"tg_chat_id": "123456789"}
    })
approval_id = resp.json()["approval_id"]

# 2. 等待用户决定
while True:
    status = requests.get(f"http://localhost:8000/v1/approvals/{approval_id}",
        headers={"Authorization": "Bearer your-key"}).json()
    if status["status"] != "pending":
        break
    time.sleep(2)

# 3. 如果批准则执行
if status["status"] == "approved":
    os.system("rm -rf ./build")
```

**或者用 curl：**

```bash
# 创建审批请求
curl -X POST http://localhost:8000/v1/approvals \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-agent",
    "action_type": "bash",
    "title": "删除 build 文件夹",
    "preview": "rm -rf ./build",
    "channel": "telegram",
    "target": {"tg_chat_id": "123456789"}
  }'

# 轮询结果
curl http://localhost:8000/v1/approvals/appr_xxx \
  -H "Authorization: Bearer your-key"
```

---

## 📱 审批按钮

### 标准模式
| 按钮 | 操作 |
|------|------|
| ✅ 批准 | 允许本次 |
| ✅ 会话 | 允许本会话 |
| ❌ 拒绝 | 拒绝 |
| ♾️ 永久 | 永久允许此类操作 |

### 问答模式
| 按钮 | 操作 |
|------|------|
| A / B / C / D | 选择选项 |
| 📝 自定义 | 输入自定义回复 |

---

## 🐳 Docker

```bash
# 启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

---

## 📝 环境变量

```bash
# 必需
APPROVAL_API_KEY=your-secret-key
TELEGRAM_BOT_TOKEN=123456:ABC...
APPROVAL_TG_CHAT_ID=your-chat-id

# 可选：Email
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=you@gmail.com
EMAIL_USERNAME=you@gmail.com
EMAIL_PASSWORD=app-password

# 可选：邮件一键按钮需要
PUBLIC_URL=https://your-domain.com
```

---

## 🤝 贡献

欢迎 PR！可以：
- 添加新的通知渠道（Slack、Discord、微信等）
- 改进 UI

---

## 🔗 为什么做这个

像 [Moltbot](https://github.com/moltbot/moltbot) 这样的自主 AI Agent 很强大，但往往缺乏内置的权限控制。它们需要读取文件、执行命令、与外部服务交互——但没有人工监督，很容易出问题。

这个项目提供了一个**独立的审批协议**，任何 Agent 都可以通过 HTTP API 集成。

**也适用于：** [Claude Code](https://docs.anthropic.com/en/docs/claude-code)（Anthropic 的 CLI Agent）

---

## 📄 许可证

MIT - 随便用。

---

<div align="center">

**如果这个项目让你不用再盯着终端，给个 ⭐ 吧**

用 ☕ 和盯终端的烦躁做的

</div>
