#!/usr/bin/env python3
"""
MCP Server for Agent Approval Gate
Provides tools for Claude Code to request approvals and ask questions via Telegram/Email
"""

import json
import sys
import os
import time
import subprocess
import uuid

# Configuration
API_BASE = os.getenv("APPROVAL_GATE_URL", "http://localhost:8000")
API_KEY = os.getenv("APPROVAL_API_KEY")
if not API_KEY:
    print("Error: APPROVAL_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)

DEFAULT_CHANNEL = os.getenv("APPROVAL_CHANNEL", "telegram")
DEFAULT_TG_CHAT_ID = os.getenv("APPROVAL_TG_CHAT_ID", "")
DEFAULT_EMAIL = os.getenv("APPROVAL_EMAIL", "")

# Generate unique session ID per MCP server process
SESSION_ID = os.getenv("APPROVAL_SESSION_ID") or f"mcp_{uuid.uuid4().hex[:12]}"


def api_call(method: str, path: str, data: dict = None) -> dict:
    """Call API using curl (more reliable than httpx in some environments)"""
    cmd = ["curl", "-sS", f"{API_BASE}{path}", "-H", f"Authorization: Bearer {API_KEY}"]
    if method == "POST":
        cmd.extend(["-X", "POST", "-H", "Content-Type: application/json", "-d", json.dumps(data)])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout else {}


def send_response(response: dict):
    print(json.dumps(response), flush=True)


def request_approval(
    action_type: str,
    title: str,
    preview: str,
    channel: str = None,
    tg_chat_id: str = None,
    email_to: str = None,
    session_id: str = None,
    expires_in_sec: int = 300,
    options: list = None
) -> dict:
    """Request approval for an action"""
    channel = channel or DEFAULT_CHANNEL
    session_id = session_id or SESSION_ID

    if channel == "telegram":
        target = {"tg_chat_id": tg_chat_id or DEFAULT_TG_CHAT_ID}
    else:
        target = {"email_to": email_to or DEFAULT_EMAIL}

    data = {
        "session_id": session_id,
        "action_type": action_type,
        "title": title,
        "preview": preview,
        "channel": channel,
        "target": target,
        "expires_in_sec": expires_in_sec
    }
    if options:
        data["options"] = options

    return api_call("POST", "/v1/approvals", data)


def check_approval(approval_id: str) -> dict:
    """Check approval status"""
    return api_call("GET", f"/v1/approvals/{approval_id}")


def wait_for_approval(approval_id: str, poll_interval: int = 3, max_wait: int = 300) -> dict:
    """Wait for approval decision (blocking)"""
    start = time.time()
    while time.time() - start < max_wait:
        result = check_approval(approval_id)
        status = result.get("status")
        if status and status != "pending":
            return result
        time.sleep(poll_interval)
    return {"status": "expired", "error": "Timeout waiting for approval"}


def execute_approved(
    command: str,
    title: str = None,
    channel: str = None,
    timeout: int = 60
) -> dict:
    """Request approval and execute command if approved"""
    channel = channel or DEFAULT_CHANNEL

    # 1. Request approval
    req_result = request_approval(
        action_type="bash_command",
        title=title or command[:50],
        preview=command,
        channel=channel,
        tg_chat_id=DEFAULT_TG_CHAT_ID if channel == "telegram" else None,
        email_to=DEFAULT_EMAIL if channel == "email" else None
    )

    if not req_result.get("approval_id"):
        return {"status": "error", "error": "Failed to create approval request", "details": req_result}

    # 2. Wait for approval
    approval = wait_for_approval(req_result["approval_id"])

    if approval.get("status") != "approved":
        return {"status": approval.get("status", "unknown"), "error": "Not approved", "approval": approval}

    # 3. Execute command
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "status": "executed",
            "approval_id": req_result["approval_id"],
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# MCP Protocol Implementation
TOOLS = [
    {
        "name": "request_approval",
        "description": "Request human approval via Telegram/Email before executing a sensitive action. Returns approval_id, then use wait_for_approval to block until decision.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Type of action (e.g., bash_command, file_write, http_request)"},
                "title": {"type": "string", "description": "Short title describing the action"},
                "preview": {"type": "string", "description": "Full details/code that will be executed"},
                "channel": {"type": "string", "enum": ["telegram", "email"], "description": "Channel to send approval request (default: telegram)"}
            },
            "required": ["action_type", "title", "preview"]
        }
    },
    {
        "name": "wait_for_approval",
        "description": "Block and wait for approval decision. Returns status: approved, denied, or expired.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "approval_id": {"type": "string", "description": "The approval_id from request_approval"}
            },
            "required": ["approval_id"]
        }
    },
    {
        "name": "ask_user",
        "description": "Ask user a question with options (A/B/C/D style). Sends to Telegram/Email and waits for response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to ask"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of options (e.g., ['Use React', 'Use Vue', 'Use Svelte'])"
                },
                "channel": {"type": "string", "enum": ["telegram", "email"], "description": "Channel to send question (default: telegram)"}
            },
            "required": ["question", "options"]
        }
    },
    {
        "name": "execute_approved",
        "description": "Request approval via Telegram/Email and execute command if approved. Bypasses Claude Code's built-in permission dialog. Use this for sensitive commands that need human approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute"},
                "title": {"type": "string", "description": "Short title for the approval request (optional)"},
                "channel": {"type": "string", "enum": ["telegram", "email"], "description": "Channel to send approval request (default: telegram)"},
                "timeout": {"type": "integer", "description": "Command execution timeout in seconds (default: 60)"}
            },
            "required": ["command"]
        }
    }
]


def handle_request(request: dict) -> dict:
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "approval-gate", "version": "1.0.0"}
            }
        }

    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        try:
            if tool_name == "request_approval":
                result = request_approval(**args)
            elif tool_name == "wait_for_approval":
                result = wait_for_approval(**args)
            elif tool_name == "ask_user":
                # 发送带选项按钮的消息
                question = args.get("question", "")
                options = args.get("options", [])
                channel = args.get("channel")  # 可选，默认使用 DEFAULT_CHANNEL

                # 使用唯一的 action_type 避免被自动批准
                import hashlib
                unique_type = "question_" + hashlib.md5(question.encode()).hexdigest()[:8]

                req_result = request_approval(
                    action_type=unique_type,
                    title=question[:50],
                    preview=question,
                    options=options,
                    channel=channel
                )
                if req_result.get("approval_id"):
                    result = wait_for_approval(req_result["approval_id"])
                    # 解析回复
                    if result.get("status") == "approved":
                        note = result.get("decision", {}).get("note", "")
                        # 如果是选项字母，转换为对应的选项文本
                        if note and len(note) == 1 and note.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            idx = ord(note.upper()) - ord('A')
                            if idx < len(options):
                                result["answer"] = options[idx]
                            else:
                                result["answer"] = note
                        else:
                            result["answer"] = note if note else "approved"
                else:
                    result = req_result
            elif tool_name == "execute_approved":
                result = execute_approved(**args)
            else:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True}
            }

    elif method == "notifications/initialized":
        return None

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response:
                send_response(response)
        except json.JSONDecodeError as e:
            send_response({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}})
        except Exception as e:
            send_response({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": f"Internal error: {e}"}})


if __name__ == "__main__":
    main()
