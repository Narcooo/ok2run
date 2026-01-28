#!/usr/bin/env python3
"""
Claude Code PermissionRequest Hook
完全接管 Claude Code 的权限确认对话框，通过 Telegram/Email 审批

使用方法：
1. 在 ~/.claude/settings.json 中添加 hook 配置
2. 运行 API 服务和 Telegram poller
3. 所有权限确认都会发送到 Telegram
"""

import json
import os
import sys
import time
import subprocess

# 配置
API_BASE = os.getenv("APPROVAL_GATE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("APPROVAL_API_KEY", "dev-key")
CHANNEL = os.getenv("APPROVAL_CHANNEL", "telegram")
TG_CHAT_ID = os.getenv("APPROVAL_TG_CHAT_ID", "")
EMAIL = os.getenv("APPROVAL_EMAIL", "")
POLL_INTERVAL = 2
MAX_WAIT = 300  # 5 minutes


def api_call(method: str, path: str, data: dict = None) -> dict:
    """Call API using curl"""
    cmd = ["curl", "-sS", f"{API_BASE}{path}", "-H", f"Authorization: Bearer {API_KEY}"]
    if method == "POST":
        cmd.extend(["-X", "POST", "-H", "Content-Type: application/json", "-d", json.dumps(data)])
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout) if result.stdout else {}
    except json.JSONDecodeError:
        return {"error": result.stdout or result.stderr}


def request_approval(tool_name: str, tool_input: dict) -> dict:
    """Request approval via Telegram/Email"""
    # 构建预览文本
    if tool_name == "Bash":
        preview = tool_input.get("command", str(tool_input))
    elif tool_name == "Write":
        preview = f"Write to: {tool_input.get('file_path', 'unknown')}\n\n{tool_input.get('content', '')[:500]}..."
    elif tool_name == "Edit":
        preview = f"Edit: {tool_input.get('file_path', 'unknown')}\n\nOld: {tool_input.get('old_string', '')[:200]}\nNew: {tool_input.get('new_string', '')[:200]}"
    else:
        preview = json.dumps(tool_input, indent=2, ensure_ascii=False)[:1000]

    # 构建 target
    if CHANNEL == "telegram":
        target = {"tg_chat_id": TG_CHAT_ID}
    else:
        target = {"email_to": EMAIL}

    data = {
        "session_id": "claude_code",
        "action_type": tool_name,
        "title": f"Claude Code: {tool_name}",
        "preview": preview,
        "channel": CHANNEL,
        "target": target,
        "expires_in_sec": MAX_WAIT
    }

    return api_call("POST", "/v1/approvals", data)


def wait_for_approval(approval_id: str) -> dict:
    """Wait for approval decision"""
    start = time.time()
    while time.time() - start < MAX_WAIT:
        result = api_call("GET", f"/v1/approvals/{approval_id}")
        status = result.get("status")
        if status and status != "pending":
            return result
        time.sleep(POLL_INTERVAL)
    return {"status": "expired"}


def main():
    # 读取 hook 输入
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # 如果没有输入，返回 ask（显示默认对话框）
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "ask"}
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "Unknown")
    tool_input = input_data.get("tool_input", {})

    # 某些工具不需要审批
    skip_tools = ["Read", "Glob", "Grep", "LS", "Task", "WebFetch", "WebSearch"]
    if tool_name in skip_tools:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"}
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # 请求审批
    req_result = request_approval(tool_name, tool_input)
    approval_id = req_result.get("approval_id")

    if not approval_id:
        # API 调用失败，回退到默认对话框
        sys.stderr.write(f"[Hook] API error: {req_result}\n")
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "ask"}
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # 如果自动批准
    if req_result.get("auto"):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"}
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # 等待审批
    result = wait_for_approval(approval_id)
    status = result.get("status")

    if status == "approved":
        decision = result.get("decision", {})
        override = decision.get("override")

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"}
            }
        }

        # 如果有 override，修改工具输入
        if override and tool_name == "Bash":
            output["hookSpecificOutput"]["decision"]["updatedInput"] = {
                "command": override
            }

        print(json.dumps(output))
        sys.exit(0)

    elif status == "denied":
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {
                    "behavior": "deny",
                    "message": "Rejected via Telegram",
                    "interrupt": False
                }
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    else:
        # 超时或其他状态，回退到默认对话框
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "ask"}
            }
        }
        print(json.dumps(output))
        sys.exit(0)


if __name__ == "__main__":
    main()
