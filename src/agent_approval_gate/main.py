import html
import os
import re

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from agent_approval_gate.adapters import EmailAdapter, TelegramAdapter
from agent_approval_gate.adapters.email import verify_action_signature
from agent_approval_gate.auth import get_client_id
from agent_approval_gate.config import get_settings
from agent_approval_gate.database import get_db, init_db
from agent_approval_gate.decision import Decision
from agent_approval_gate.schemas import (
    ApprovalCreateRequest,
    ApprovalCreateResponse,
    ApprovalStatusResponse,
    EmailReplyIn,
)
from agent_approval_gate.service import (
    apply_decision,
    create_approval,
    expire_if_needed,
    get_approval,
    get_approval_no_check,
    revoke_allow_rule,
    validate_target,
)
from agent_approval_gate.simulate import simulate_email_reply
from agent_approval_gate.utils import to_epoch

app = FastAPI(title="Agent Approval Gate")

# Telegram Webhook 相关
ALLOWED_USER_IDS = set(uid.strip() for uid in os.getenv("ALLOWED_USER_IDS", "").split(",") if uid.strip())

telegram_adapter = TelegramAdapter()
email_adapter = EmailAdapter()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def decision_payload(approval):
    if not approval.decision_code:
        return None
    return {
        "code": approval.decision_code,
        "note": approval.decision_note,
        "override": approval.decision_override,
    }


@app.post("/v1/approvals", response_model=ApprovalCreateResponse)
def create_approval_endpoint(
    request: ApprovalCreateRequest,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    target = validate_target(request.channel, request.target)
    approval, auto = create_approval(
        db,
        session_id=request.session_id,
        action_type=request.action_type,
        title=request.title,
        preview=request.preview,
        channel=request.channel,
        target=target,
        expires_in_sec=request.expires_in_sec,
        client_id=client_id,
    )

    if not auto:
        if request.channel == "telegram":
            if request.options:
                telegram_adapter.send_question(approval, request.options)
            else:
                telegram_adapter.send_approval(approval)
        else:
            if request.options:
                email_adapter.send_question(approval, request.options)
            else:
                email_adapter.send_approval(approval)

    response = {
        "approval_id": approval.approval_id,
        "status": approval.status,
        "auto": auto,
    }
    if auto:
        response["decision"] = decision_payload(approval)
    else:
        response["expires_at"] = to_epoch(approval.expires_at)
    return response


@app.get("/v1/approvals/{approval_id}", response_model=ApprovalStatusResponse)
def get_approval_endpoint(
    approval_id: str,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    approval = get_approval(db, approval_id)
    if approval.client_id != client_id:
        raise HTTPException(status_code=404, detail="approval not found")
    approval = expire_if_needed(db, approval)

    response = {"status": approval.status}
    if approval.status == "pending":
        response["expires_at"] = to_epoch(approval.expires_at)
        return response

    response["expires_at"] = to_epoch(approval.expires_at)
    response["decision"] = decision_payload(approval)
    response["session_id"] = approval.session_id
    response["action_type"] = approval.action_type
    return response


@app.post("/v1/inbox/email-reply")
def email_reply_endpoint(
    payload: EmailReplyIn,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    approval = simulate_email_reply(db, payload.subject, payload.body, client_id=client_id)
    return {"status": approval.status, "approval_id": approval.approval_id}


@app.delete("/v1/allow-rules/{rule_id}")
def revoke_allow_rule_endpoint(
    rule_id: str,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    rule = revoke_allow_rule(db, rule_id, client_id=client_id)
    return {
        "rule_id": rule.rule_id,
        "status": "revoked",
        "client_id": client_id,
        "action_type": rule.action_type,
    }


# HTML 响应模板
def _action_html(title: str, message: str, success: bool = True) -> str:
    color = "#22c55e" if success else "#ef4444"
    icon = "✅" if success else "❌"
    # Escape HTML entities to prevent XSS
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             background-color: #f3f4f6; margin: 0; padding: 40px; text-align: center;">
    <div style="max-width: 400px; margin: 0 auto; background-color: white;
                border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 40px;">
        <div style="font-size: 64px; margin-bottom: 20px;">{icon}</div>
        <h1 style="color: {color}; margin: 0 0 16px 0; font-size: 24px;">{safe_title}</h1>
        <p style="color: #64748b; margin: 0; font-size: 16px;">{safe_message}</p>
    </div>
</body>
</html>
"""


def _note_form_html(approval_id: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Add Note</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             background-color: #f3f4f6; margin: 0; padding: 40px; text-align: center;">
    <div style="max-width: 400px; margin: 0 auto; background-color: white;
                border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 40px;">
        <div style="font-size: 64px; margin-bottom: 20px;">📝</div>
        <h1 style="color: #3b82f6; margin: 0 0 16px 0; font-size: 24px;">Add Note</h1>
        <form action="/v1/action/{approval_id}/submit_note" method="get">
            <textarea name="note" rows="4" style="width: 100%; padding: 12px; border: 1px solid #e2e8f0;
                border-radius: 8px; font-size: 14px; resize: vertical; box-sizing: border-box;"
                placeholder="Enter your note here..."></textarea>
            <button type="submit" style="margin-top: 16px; padding: 12px 32px; background-color: #22c55e;
                color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer;
                font-weight: bold;">Approve with Note</button>
        </form>
    </div>
</body>
</html>"""


def _custom_form_html(approval_id: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Custom Reply</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             background-color: #f3f4f6; margin: 0; padding: 40px; text-align: center;">
    <div style="max-width: 400px; margin: 0 auto; background-color: white;
                border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 40px;">
        <div style="font-size: 64px; margin-bottom: 20px;">📝</div>
        <h1 style="color: #3b82f6; margin: 0 0 16px 0; font-size: 24px;">Custom Reply</h1>
        <form action="/v1/action/{approval_id}/submit_custom" method="get">
            <textarea name="reply" rows="4" style="width: 100%; padding: 12px; border: 1px solid #e2e8f0;
                border-radius: 8px; font-size: 14px; resize: vertical; box-sizing: border-box;"
                placeholder="Enter your custom reply..."></textarea>
            <button type="submit" style="margin-top: 16px; padding: 12px 32px; background-color: #3b82f6;
                color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer;
                font-weight: bold;">Submit</button>
        </form>
    </div>
</body>
</html>"""


@app.get("/v1/action/{approval_id}/{action}", response_class=HTMLResponse)
def action_endpoint(approval_id: str, action: str, sig: str = "", note: str = "", reply: str = "", db=Depends(get_db)):
    """处理邮件按钮点击（一键审批）"""
    settings = get_settings()

    # 验证签名（如果配置了 ACTION_SIGN_KEY）
    if settings.action_sign_key:
        if not sig or not verify_action_signature(approval_id, action, sig, settings.action_sign_key):
            return HTMLResponse(_action_html("Invalid Link", "This link is invalid or has been tampered with.", False), status_code=403)

    try:
        approval = get_approval_no_check(db, approval_id)
    except HTTPException:
        return HTMLResponse(_action_html("Not Found", "Approval request not found.", False), status_code=404)

    if approval.status != "pending":
        return HTMLResponse(_action_html("Already Processed", f"This request was already {approval.status}.", False))

    # 解析 action: approve, session, deny, note, always, option_A, option_B, etc.
    code_map = {"approve": "1", "session": "2", "deny": "3", "always": "6"}

    if action == "note":
        # 显示备注输入表单
        return HTMLResponse(_note_form_html(approval_id))
    elif action == "custom_form":
        # 显示自定义输入表单
        return HTMLResponse(_custom_form_html(approval_id))
    elif action == "submit_note":
        # 处理备注提交
        decision = Decision(code="4", note=note or None, override=None)
        try:
            apply_decision(db, approval, decision)
        except HTTPException as e:
            return HTMLResponse(_action_html("Error", e.detail, False), status_code=e.status_code)
        return HTMLResponse(_action_html("Approved with Note", f"Note: {note}" if note else "Approved"))
    elif action == "submit_custom":
        # 处理自定义回复提交
        decision = Decision(code="4", note=reply or None, override=None)
        try:
            apply_decision(db, approval, decision)
        except HTTPException as e:
            return HTMLResponse(_action_html("Error", e.detail, False), status_code=e.status_code)
        return HTMLResponse(_action_html("Reply Submitted", f"Your reply: {reply}" if reply else "Submitted"))
    elif action in code_map:
        code = code_map[action]
        note = None
    elif action.startswith("option_"):
        # option_A, option_B, option_C, option_D
        code = "4"  # 选择题回复
        note = action.replace("option_", "")
    else:
        return HTMLResponse(_action_html("Invalid Action", f"Unknown action: {action}", False), status_code=400)

    decision = Decision(code=code, note=note, override=None)
    try:
        apply_decision(db, approval, decision)
    except HTTPException as e:
        return HTMLResponse(_action_html("Error", e.detail, False), status_code=e.status_code)

    action_text = {
        "approve": "Approved",
        "session": "Approved for Session",
        "deny": "Denied",
        "always": "Always Allowed",
    }.get(action, f"Selected: {note}")

    return HTMLResponse(_action_html(action_text, f"Request {approval_id} has been processed."))


# ============ Telegram Webhook ============

TEXTS = {
    "zh": {
        "no_permission": "⛔ 无权限操作",
        "invalid": "无效的操作",
        "selected": "已选择",
        "approved": "已批准",
        "denied": "已拒绝",
        "failed": "处理失败",
        "enter_custom": "请输入自定义回复",
        "reply_received": "已收到回复",
    },
    "en": {
        "no_permission": "⛔ No permission",
        "invalid": "Invalid action",
        "selected": "Selected",
        "approved": "Approved",
        "denied": "Denied",
        "failed": "Failed",
        "enter_custom": "Please enter custom reply",
        "reply_received": "Reply received",
    }
}


def _get_lang(language_code: str | None) -> str:
    if language_code and language_code.startswith("zh"):
        return "zh"
    return "en"


def _t(key: str, lang: str) -> str:
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)


def _tg_api_call(method: str, data: dict) -> dict:
    settings = get_settings()
    url = f"{settings.telegram_api_base}/bot{settings.telegram_bot_token}/{method}"
    try:
        resp = httpx.post(url, data=data, timeout=10)
        return resp.json()
    except Exception:
        return {}


def _answer_callback(callback_query_id: str, text: str):
    _tg_api_call("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})


def _edit_message(chat_id: int, message_id: int, text: str):
    import json
    _tg_api_call("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({"inline_keyboard": []})
    })


def _send_message(chat_id: int, text: str, reply_markup: dict = None):
    import json
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    _tg_api_call("sendMessage", data)


def _process_tg_approval(approval_id: str, code: str, note: str = None, db=None) -> dict:
    """处理 Telegram 审批"""
    try:
        approval = get_approval_no_check(db, approval_id)
        if approval.status != "pending":
            # 返回实际状态，而不是 "already_processed"
            return {"status": "already_processed", "actual_status": approval.status}
        decision = Decision(code=code, note=note, override=None)
        updated_approval = apply_decision(db, approval, decision)
        return {"status": updated_approval.status}
    except HTTPException as e:
        return {"status": "error", "detail": e.detail}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/v1/telegram/webhook")
async def telegram_webhook(request: Request, db=Depends(get_db)):
    """Telegram Webhook 端点 - 处理按钮点击和文本回复"""
    # 验证 Telegram secret token
    settings = get_settings()
    if settings.telegram_webhook_secret:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    # 处理按钮点击
    if "callback_query" in update:
        callback = update["callback_query"]
        callback_id = callback["id"]
        data = callback.get("data", "")
        message = callback.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        original_text = message.get("text", "")

        user = callback.get("from", {})
        user_id = str(user.get("id", ""))
        lang = _get_lang(user.get("language_code"))

        # 安全检查
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            _answer_callback(callback_id, _t("no_permission", lang))
            return {"ok": True}

        if ":" not in data:
            _answer_callback(callback_id, _t("invalid", lang))
            return {"ok": True}

        approval_id, code = data.split(":", 1)

        # 处理选择题选项
        if code.startswith("opt:"):
            option = code.split(":")[1]
            if option == "custom":
                _answer_callback(callback_id, "")
                _send_message(chat_id, f"📝 <code>{approval_id}</code>", {
                    "force_reply": True,
                    "selective": True,
                    "input_field_placeholder": _t("enter_custom", lang)
                })
                return {"ok": True}

            result = _process_tg_approval(approval_id, "4", option, db)
            status = result.get("status")
            if status in ("approved", "denied"):
                _answer_callback(callback_id, f"{_t('selected', lang)}: {option}")
                new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n✅ <b>{_t('selected', lang)}: {option}</b>"
                _edit_message(chat_id, message_id, new_text)
            elif status == "already_processed":
                # 显示实际状态
                actual = result.get("actual_status", "approved")
                if actual == "approved":
                    _answer_callback(callback_id, "⚡ " + _t("approved", lang))
                    new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n⚡ <b>{_t('approved', lang)}</b>"
                else:
                    _answer_callback(callback_id, "⚡ " + _t("denied", lang))
                    new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n⚡ <b>{_t('denied', lang)}</b>"
                _edit_message(chat_id, message_id, new_text)
            else:
                _answer_callback(callback_id, f"{_t('failed', lang)}: {status}")
            return {"ok": True}

        # 处理标准审批按钮
        code_info = {
            "1": ("✅", "approve"),
            "2": ("✅", "approve_session"),
            "3": ("❌", "deny"),
            "6": ("♾️", "always_allow")
        }
        emoji, _ = code_info.get(code, ("", code))
        result = _process_tg_approval(approval_id, code, None, db)
        status = result.get("status")

        if status in ("approved", "denied"):
            status_text = _t("approved", lang) if status == "approved" else _t("denied", lang)
            _answer_callback(callback_id, f"{emoji} {status_text}")
            status_emoji = "✅" if status == "approved" else "❌"
            new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n{status_emoji} <b>{status_text}</b>"
            _edit_message(chat_id, message_id, new_text)
        elif status == "already_processed":
            # 显示实际状态
            actual = result.get("actual_status", "approved")
            if actual == "approved":
                _answer_callback(callback_id, "⚡ " + _t("approved", lang))
                new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n⚡ <b>{_t('approved', lang)}</b>"
            else:
                _answer_callback(callback_id, "⚡ " + _t("denied", lang))
                new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n⚡ <b>{_t('denied', lang)}</b>"
            _edit_message(chat_id, message_id, new_text)
        else:
            _answer_callback(callback_id, f"{_t('failed', lang)}: {status}")

    # 处理文本回复
    elif "message" in update:
        msg = update["message"]
        text = msg.get("text", "").strip()
        reply_to = msg.get("reply_to_message", {})
        reply_text = reply_to.get("text", "")
        chat_id = msg.get("chat", {}).get("id")

        user = msg.get("from", {})
        user_id = str(user.get("id", ""))
        lang = _get_lang(user.get("language_code"))

        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            return {"ok": True}

        # 提取 approval_id
        match = re.search(r"(appr_[a-f0-9]+)", reply_text)
        if not match:
            return {"ok": True}

        approval_id = match.group(1)
        result = _process_tg_approval(approval_id, "4", text, db)

        if result.get("status") in ("approved", "denied"):
            _send_message(chat_id, f"✅ {_t('reply_received', lang)}\n\n{text}")

    return {"ok": True}


@app.post("/v1/telegram/setup-webhook")
def setup_telegram_webhook(
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    """设置 Telegram Webhook"""
    settings = get_settings()
    if not settings.public_url:
        raise HTTPException(status_code=400, detail="PUBLIC_URL not configured")

    webhook_url = f"{settings.public_url}/v1/telegram/webhook"
    url = f"{settings.telegram_api_base}/bot{settings.telegram_bot_token}/setWebhook"

    # 构建请求数据，包含 secret_token（如果配置了）
    data = {"url": webhook_url}
    if settings.telegram_webhook_secret:
        data["secret_token"] = settings.telegram_webhook_secret

    try:
        resp = httpx.post(url, data=data, timeout=10)
        return {"webhook_url": webhook_url, "telegram_response": resp.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/telegram/webhook")
def delete_telegram_webhook(
    client_id: str = Depends(get_client_id),
):
    """删除 Telegram Webhook（恢复轮询模式）"""
    settings = get_settings()
    url = f"{settings.telegram_api_base}/bot{settings.telegram_bot_token}/deleteWebhook"

    try:
        resp = httpx.post(url, timeout=10)
        return {"telegram_response": resp.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
