# agent-approval-gate

![CI](https://github.com/Narcooo/ok2run/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

[English](README.md) | 中文

面向 Agent 的自托管审批门闸：通过 Telegram 或 Email 发送“菜单式一次回复”，无前端。

## 特性亮点
- 一次回复菜单（1..6），支持 note/override。
- Telegram + Email 适配器（默认 Telegram mock）。
- 永久允许（allow rules）+ 会话允许（session allows）自动放行。
- SQLite 默认存储，SQLAlchemy 可切 Postgres。
- FastAPI，自动生成 OpenAPI `/openapi.json`。

## 快速开始（Docker Compose）
1) 复制环境变量模板：
```bash
cp .env.example .env
```
2) 启动服务：
```bash
docker compose up --build
```
3) 打开：
- API 文档：`http://localhost:8000/docs`
- OpenAPI：`http://localhost:8000/openapi.json`
- MailHog：`http://localhost:8025`

## 菜单协议（单条回复）
| 代码 | 含义 | payload |
| --- | --- | --- |
| 1 | 仅此次允许 | 无 |
| 2 | 本次会话允许 | 无 |
| 3 | 拒绝 | 无 |
| 4 | 允许并添加备注 | 必填文本 |
| 5 | 修改后允许 | 必填文本 |
| 6 | 永久允许该 action_type | 无 |

解析规则：
- 去除首尾空白；第一个 token 为 code（1..6）。
- 剩余内容为 payload_text。
- code 为 4/5 时，payload 必填，否则 invalid。

## API 概览
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/v1/approvals` | 创建审批（命中规则时自动放行） |
| GET | `/v1/approvals/{approval_id}` | 查询审批状态 + decision |
| POST | `/v1/inbox/email-reply` | 接收邮件回复（无 IMAP） |
| DELETE | `/v1/allow-rules/{rule_id}` | 撤销永久允许 |

## 示例

创建审批（Telegram）：
```bash
curl -sS -X POST http://localhost:8000/v1/approvals \
  -H 'Authorization: Bearer dev-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "sess_123",
    "action_type": "exec_cmd",
    "title": "Run command",
    "preview": "rm -rf ./build && npm run build",
    "channel": "telegram",
    "target": {"tg_chat_id": "123456789"},
    "expires_in_sec": 600
  }'
```

创建审批（Email）：
```bash
curl -sS -X POST http://localhost:8000/v1/approvals \
  -H 'Authorization: Bearer dev-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "sess_123",
    "action_type": "http_request",
    "title": "POST request",
    "preview": "POST https://api.example.com/pay ...",
    "channel": "email",
    "target": {"email_to": "you@domain.com"},
    "expires_in_sec": 600
  }'
```

查询审批状态：
```bash
curl -sS -H 'Authorization: Bearer dev-key' \
  http://localhost:8000/v1/approvals/appr_xxx
```

邮件回复接入：
```bash
curl -sS -X POST http://localhost:8000/v1/inbox/email-reply \
  -H 'Authorization: Bearer dev-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "Run command [appr_xxx]",
    "body": "4 please add logs\n\nOn Tue..."
  }'
```

撤销永久允许：
```bash
curl -sS -X DELETE \
  -H 'Authorization: Bearer dev-key' \
  http://localhost:8000/v1/allow-rules/rule_xxx
```

## 配置

鉴权：
- `Authorization: Bearer <APPROVAL_API_KEY>`
- `client_id = sha256(api_key)[:12]`

Telegram：
- 设置 `TELEGRAM_BOT_TOKEN` 启用真实发送。
- 设置 `TELEGRAM_MOCK=1` 用于本地和测试。

Email：
- SMTP 使用 `EMAIL_SMTP_*` 配置。
- 邮件回复通过 `POST /v1/inbox/email-reply` 接入（无 IMAP）。

## 全流程邮箱体验（Gmail + Apps Script + ngrok）
目标：你执行任务 → 系统发邮件 → 你在邮箱里回复 → 自动回写审批结果。

步骤一：配置并启动服务
```bash
cp .env.example .env
# 在 .env 里填 Gmail SMTP（EMAIL_SMTP_*）
docker compose up -d --build
```

步骤二：把本地 API 暴露到公网（任选其一）
```bash
ngrok http 8000
```
把得到的公网地址记为 `https://xxxxx.ngrok-free.app`。

步骤三：配置 Gmail Apps Script（自动转发邮件回复）
1) 打开 https://script.google.com，新建项目。  
2) 将 `scripts/gmail_inbound.gs` 全量粘贴进去。  
3) 在 **项目设置 → 脚本属性** 添加：  
   - `APPROVAL_GATE_URL` = `https://xxxxx.ngrok-free.app`  
   - `APPROVAL_API_KEY` = 你的 API key  
   - `GMAIL_QUERY` = `is:unread subject:(appr_)`（可改）  
4) 设置触发器：每分钟执行 `processApprovalReplies`。  

步骤四：触发审批（Codex/CLI）
```bash
python scripts/request_approval.py \
  --session-id sess_demo \
  --action-type exec_cmd \
  --title \"Run command\" \
  --preview \"npm test\" \
  --channel email \
  --email-to 你的gmail地址
```
然后你会在 Gmail 里收到审批邮件，直接回复 `1/2/3/4 .../5 .../6` 即可完成审批。

## Agent 接入流程（request -> poll）
1) POST `/v1/approvals`（带 `session_id` + `action_type` + `preview`）。
2) 轮询 GET `/v1/approvals/{approval_id}` 直到状态不再 pending。
3) 如果有 `decision.override`，按 override 执行；被拒绝则停止。

## 测试
```bash
pytest -q
```

E2E 演示：
```bash
python scripts/e2e_demo.py
```

## 文档
- 协议与数据模型：`DESIGN.md`
- OpenAPI：`/openapi.json`
