# Agent Approval Gate

![License](https://img.shields.io/badge/license-MIT-green.svg)

[English](README.md) | 中文

AI Agent 人工审批系统。在执行敏感命令前，通过 Telegram/Email 获取人工批准。

## 特性

- **一键审批** - Telegram 或 Email 按钮点击即可
- **Claude Code 集成** - 通过 MCP 协议无缝对接
- **绕过内置对话框** - Telegram 批准后直接执行，无需再次确认
- **向用户提问** - 支持 A/B/C/D 选项 + 自定义输入
- **会话 & 永久规则** - 自动批准重复操作
- **自托管** - 数据完全在你的服务器上

## 快速开始

### 1. 安装 & 运行

```bash
# 克隆
git clone https://github.com/user/agent-approval-gate.git
cd agent-approval-gate

# 配置
cp .env.example .env
# 编辑 .env，填入你的 Telegram Bot Token 和邮箱设置

# 运行 API 服务
pip install -r requirements.txt
python -m uvicorn src.agent_approval_gate.main:app --host 0.0.0.0 --port 8000

# 运行 Telegram 轮询器（另开终端）
python scripts/telegram_poller.py
```

### 2. 配置 Claude Code

在项目的 `.mcp.json` 中添加：

```json
{
  "mcpServers": {
    "approval-gate": {
      "command": "python",
      "args": ["/path/to/agent-approval-gate/mcp_server.py"],
      "env": {
        "APPROVAL_GATE_URL": "http://127.0.0.1:8000",
        "APPROVAL_API_KEY": "your-api-key",
        "APPROVAL_TG_CHAT_ID": "your-telegram-chat-id",
        "APPROVAL_EMAIL": "your@email.com"
      }
    }
  }
}
```

### 3. 获取 Telegram Chat ID

1. 通过 [@BotFather](https://t.me/BotFather) 创建机器人
2. 向你的机器人发送 `/start`
3. 访问 `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. 在返回结果中找到 `chat.id`

## 在 Claude Code 中使用

### 审批后执行（推荐）

使用 `execute_approved` 在 Telegram/Email 批准后执行命令：

```
用户: 删除 build 文件夹

Claude: 我先请求审批。
[调用 mcp__approval-gate__execute_approved]
  command: "rm -rf ./build"
  title: "删除 build 文件夹"

[Telegram 收到通知]
[用户点击"批准"按钮]
[命令直接执行 - 无 Claude Code 确认对话框]

结果: Build 文件夹已删除。
```

### 向用户提问

使用 `ask_user` 获取用户输入：

```
用户: 用什么数据库？

Claude: 让我问一下。
[调用 mcp__approval-gate__ask_user]
  question: "这个项目用什么数据库？"
  options: ["PostgreSQL", "MySQL", "SQLite"]

[Telegram 显示按钮: A) PostgreSQL  B) MySQL  C) SQLite  📝 自定义]
[用户点击选项或输入自定义答案]

结果: 用户选择了 PostgreSQL。
```

### 手动审批流程

需要更多控制时，使用 `request_approval` + `wait_for_approval`：

```python
# 1. 请求审批
result = mcp__approval-gate__request_approval(
    action_type="bash_command",
    title="部署到生产环境",
    preview="kubectl apply -f deploy.yaml"
)

# 2. 等待决定
approval = mcp__approval-gate__wait_for_approval(
    approval_id=result["approval_id"]
)

# 3. 检查结果
if approval["status"] == "approved":
    # 执行操作
else:
    # 操作被拒绝
```

## MCP 工具

| 工具 | 描述 |
|------|------|
| `execute_approved` | 请求审批并在批准后执行命令。**绕过 Claude Code 内置对话框。** |
| `ask_user` | 向用户提问（A/B/C/D 选项 + 自定义输入） |
| `request_approval` | 请求审批，返回 approval_id |
| `wait_for_approval` | 等待审批决定 |

## 审批按钮

### 标准审批模式
- ✅ **批准** - 允许本次操作
- ✅ **会话批准** - 允许本会话内相同操作（自动批准）
- ❌ **拒绝** - 拒绝本次操作
- ♾️ **永久允许** - 永久允许此类操作

### 问答模式
- **A/B/C/D** - 选择选项
- 📝 **自定义** - 输入自定义回复

## 环境变量

```bash
# API
APPROVAL_API_KEY=your-secret-key

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC...
APPROVAL_TG_CHAT_ID=your-chat-id

# Email（可选）
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=your@gmail.com
EMAIL_USERNAME=your@gmail.com
EMAIL_PASSWORD=app-password
APPROVAL_EMAIL=your@gmail.com

# 一键邮件按钮（可选，需要公网 URL）
PUBLIC_URL=https://your-domain.com
```

## API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/v1/approvals` | 创建审批请求 |
| GET | `/v1/approvals/{id}` | 获取审批状态 |
| POST | `/v1/inbox/email-reply` | 处理邮件/Telegram 回复 |
| GET | `/v1/action/{id}/{action}` | 一键审批（邮件按钮用） |

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Claude Code │────▶│  MCP Server │────▶│   API       │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
             ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
             │  Telegram   │          │    Email    │          │  Database   │
             │   Poller    │          │   (SMTP)    │          │  (SQLite)   │
             └─────────────┘          └─────────────┘          └─────────────┘
```

## 许可证

MIT
