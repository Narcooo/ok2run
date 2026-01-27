# agent-approval-gate

![CI](https://github.com/Narcooo/ok2run/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

English | [Chinese](README_CN.md)

Self-hosted approval gate for agent actions with a single-reply menu over Telegram or Email. No frontend.

## Highlights
- Single-reply menu (1..6) with optional note/override.
- Telegram + Email adapters (Telegram mock by default).
- Allow rules (permanent) + session allows (auto-approve).
- SQLite storage, Postgres-ready via SQLAlchemy.
- FastAPI with auto-generated OpenAPI at `/openapi.json`.

## Quick start (Docker Compose)
1) Copy env template:
```bash
cp .env.example .env
```
2) Start services:
```bash
docker compose up --build
```
3) Open docs:
- API docs: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
- MailHog UI: `http://localhost:8025`

## Menu protocol (one reply)
| Code | Meaning | Payload |
| --- | --- | --- |
| 1 | Allow once | None |
| 2 | Allow for this session | None |
| 3 | Deny | None |
| 4 | Allow once + add note | Required text |
| 5 | Modify then allow | Required text |
| 6 | Always allow this action type | None |

Parsing rules:
- Trim whitespace; first token is the code (1..6).
- Remainder is payload_text.
- Codes 4/5 require payload_text, otherwise invalid.

## API overview
| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/v1/approvals` | Create approval (auto-approve if rule/session allow hits) |
| GET | `/v1/approvals/{approval_id}` | Poll approval status + decision |
| POST | `/v1/inbox/email-reply` | Ingest email reply (no IMAP) |
| DELETE | `/v1/allow-rules/{rule_id}` | Revoke allow rule |

## Examples

Create approval (Telegram):
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

Create approval (Email):
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

Poll approval status:
```bash
curl -sS -H 'Authorization: Bearer dev-key' \
  http://localhost:8000/v1/approvals/appr_xxx
```

Email reply ingestion:
```bash
curl -sS -X POST http://localhost:8000/v1/inbox/email-reply \
  -H 'Authorization: Bearer dev-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "Run command [appr_xxx]",
    "body": "4 please add logs\n\nOn Tue..."
  }'
```

Revoke allow rule:
```bash
curl -sS -X DELETE \
  -H 'Authorization: Bearer dev-key' \
  http://localhost:8000/v1/allow-rules/rule_xxx
```

## Configuration

Auth:
- `Authorization: Bearer <APPROVAL_API_KEY>`
- `client_id = sha256(api_key)[:12]`

Telegram:
- Set `TELEGRAM_BOT_TOKEN` to enable real sends.
- Set `TELEGRAM_MOCK=1` to disable network sends (tests and local dev).

Email:
- SMTP config via `EMAIL_SMTP_*`.
- Reply ingestion is via `POST /v1/inbox/email-reply` (no IMAP required).

## Agent integration (request -> poll)
1) POST `/v1/approvals` with `session_id` + `action_type` + `preview`.
2) Poll GET `/v1/approvals/{approval_id}` until status != pending.
3) If approved with `decision.override`, use the override; if denied, stop.

## Tests
```bash
pytest -q
```

E2E demo:
```bash
python scripts/e2e_demo.py
```

## Docs
- Protocol and data model: `DESIGN.md`
- OpenAPI: `/openapi.json`
