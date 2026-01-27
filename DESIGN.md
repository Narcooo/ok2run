# Self-hosted Agent Approval Gate - Design

## Goal
Implement a self-hosted approval gate for agent actions with side effects. Humans approve or deny with a **single reply** via Telegram or Email. The gate returns `approved/denied` and optional `note/override` for the agent to continue.

Constraints:
- No frontend; Telegram/Email only.
- Single reply (no multi-turn dialog unless reply is invalid).
- Support session allow and permanent allow rules (TTL not required).
- Default self-host, no public service.

## Core concepts

### Approval
Lifecycle: `pending -> approved | denied | expired`

Fields:
- `approval_id`: string like `appr_...`
- `created_at`, `expires_at`
- `status`: `pending | approved | denied | expired`
- `session_id`: agent run/session identifier
- `action_type`: coarse action type
- `title`: short title
- `preview`: human-facing preview
- `choices`: fixed menu (see below)
- `decision_code`: final decision code
- `note`: optional human note
- `override`: optional replacement text
- `channel`: `telegram | email`
- `target`: telegram chat id or email address
- `client_id`: derived from API key
- `allow_rule_applied`: rule_id if auto-approved via allow rule

### Allow Rule (permanent allow)
Simple rule: permanently allow `client_id + action_type`.

Fields:
- `rule_id`
- `client_id`
- `action_type`
- `enabled`
- `created_at`

Match logic:
- On `POST /v1/approvals`, if a matching enabled rule exists, return `approved` and do not send a message.

### Session Allow
Lightweight allowlist for `client_id + session_id + action_type`.

Fields:
- `client_id`
- `session_id`
- `action_type`
- `created_at`

Match logic:
- On `POST /v1/approvals`, if a matching session allow exists, return `approved` and do not send a message.
- When human selects menu option 2, insert a session allow.

### Action Type
Suggested coarse types:
- `exec_cmd`
- `http_request`
- `write_file`
- `send_message`
- `custom:<tool_or_skill_name>`

## Menu protocol (single reply)

Fixed menu (do not change per request):
1) Allow once
2) Allow for this session
3) Deny
4) Allow once + add note (reply: 4 <text>)
5) Modify then allow (reply: 5 <replacement>)
6) Always allow this action type (until revoked)

Parsing:
- Trim whitespace.
- First token is the code (1..6).
- Remainder is payload_text.
- Codes 4/5 require payload_text; otherwise invalid.

Semantics:
- `1`: allow once
- `2`: allow for this session (server stores session allow)
- `3`: deny
- `4`: allow once + note (note stored)
- `5`: allow once with override (override stored)
- `6`: create allow rule for client_id + action_type

Override semantics: gate returns the raw override string to the agent; it does not interpret it.

## Channels

### Telegram
- Send approval message with: title, preview, menu, approval_id, expires_at.
- Inline buttons cover 1/2/3/6 (no text input needed).
- Options 4/5 are provided via replying with text (e.g., `4 ...`).
- Bot message includes approval_id and asks user to reply to the message.

### Email
- Send approval email: subject includes `[appr_xxx]`, body includes preview, menu, approval_id, expires_at.
- Users reply with a single line like `1` or `4 add logs`.
- Parse only the first text block of the reply (truncate quoted text and signature).
- Approval id is extracted from subject or body.

## HTTP API

Authentication:
- `Authorization: Bearer <APPROVAL_API_KEY>`
- `client_id = sha256(api_key)[:12]`

### POST /v1/approvals
Create approval.

Request:
```json
{
  "session_id": "sess_123",
  "action_type": "exec_cmd",
  "title": "Run command",
  "preview": "rm -rf ./build && npm run build",
  "channel": "telegram",
  "target": { "tg_chat_id": "123456789" },
  "expires_in_sec": 600
}
```

Email:
```json
{
  "session_id": "sess_123",
  "action_type": "http_request",
  "title": "POST request",
  "preview": "POST https://api.example.com/pay ...",
  "channel": "email",
  "target": { "email_to": "you@domain.com" },
  "expires_in_sec": 600
}
```

Response (auto-approved via allow rule or session allow):
```json
{
  "approval_id": "appr_xxx",
  "status": "approved",
  "auto": true,
  "decision": { "code": "6" }
}
```

Response (pending):
```json
{
  "approval_id": "appr_xxx",
  "status": "pending",
  "auto": false,
  "expires_at": 1730000000
}
```

### GET /v1/approvals/{approval_id}
Query approval status.

Pending:
```json
{ "status": "pending", "expires_at": 1730000000 }
```

Approved:
```json
{
  "status": "approved",
  "decision": { "code": "2", "note": null, "override": null },
  "session_id": "sess_123",
  "action_type": "exec_cmd"
}
```

Approved with note:
```json
{ "status": "approved", "decision": { "code": "4", "note": "add logs", "override": null } }
```

Approved with override:
```json
{ "status": "approved", "decision": { "code": "5", "note": null, "override": "npm test" } }
```

### POST /v1/inbox/email-reply
Accept email replies from a forwarding service.

Request:
```json
{ "subject": "Run command [appr_xxx]", "body": "4 add logs\n\nOn Tue..." }
```

### DELETE /v1/allow-rules/{rule_id}
Revoke a permanent allow rule.

## Storage
Default storage: SQLite (`data.db`) with SQLAlchemy. Postgres-compatible by swapping the URL.

Tables:
- `approvals`
- `allow_rules`
- `session_allows`

## Tests
- Unit: menu parsing, email truncation, allow rule matching, session allow matching.
- Integration: create approval -> simulate reply -> get status.
- Email adapter: send via local SMTP debug server.
- E2E: `scripts/e2e_demo.py` (create approval -> simulate reply -> query status).
