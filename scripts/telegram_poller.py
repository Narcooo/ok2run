#!/usr/bin/env python3
"""
Telegram 轮询脚本：接收按钮点击并处理审批
"""

import json
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("APPROVAL_API_KEY") or os.getenv("API_KEY", "dev-key")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 允许的 Telegram 用户 ID（只有这些用户可以审批）
ALLOWED_USER_IDS = set(filter(None, os.getenv("ALLOWED_USER_IDS", "").split(",")))

last_update_id = 0

# 国际化文本
TEXTS = {
    "zh": {
        "no_permission": "⛔ 无权限操作",
        "invalid": "无效的操作",
        "selected": "已选择",
        "approved": "已批准",
        "denied": "已拒绝",
        "action": "操作",
        "failed": "处理失败",
        "enter_note": "请输入备注内容",
        "enter_custom": "请输入自定义回复",
        "reply_below": "请回复下方消息输入备注",
        "reply_received": "已收到回复",
        "content": "内容",
    },
    "en": {
        "no_permission": "⛔ No permission",
        "invalid": "Invalid action",
        "selected": "Selected",
        "approved": "Approved",
        "denied": "Denied",
        "action": "Action",
        "failed": "Failed",
        "enter_note": "Please enter your note",
        "enter_custom": "Please enter custom reply",
        "reply_below": "Please reply to enter note",
        "reply_received": "Reply received",
        "content": "Content",
    }
}


def get_lang(language_code: str | None) -> str:
    if language_code and language_code.startswith("zh"):
        return "zh"
    return "en"


def t(key: str, lang: str) -> str:
    return TEXTS.get(lang, TEXTS["en"]).get(key, key)


def get_updates():
    global last_update_id
    url = f"{TG_API}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 30}
    try:
        resp = httpx.get(url, params=params, timeout=35)
        data = resp.json()
        if data.get("ok"):
            return data.get("result", [])
    except Exception as e:
        print(f"[Poller] Error: {e}")
    return []


def answer_callback(callback_query_id: str, text: str):
    url = f"{TG_API}/answerCallbackQuery"
    httpx.post(url, data={"callback_query_id": callback_query_id, "text": text})


def edit_message(chat_id: int, message_id: int, text: str):
    url = f"{TG_API}/editMessageText"
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({"inline_keyboard": []})
    }
    httpx.post(url, data=data)


def process_approval(approval_id: str, code: str) -> dict:
    """调用 API 处理审批"""
    try:
        print(f"[Poller] Calling API: {API_BASE}/v1/inbox/email-reply")
        print(f"[Poller] approval_id={approval_id}, code={code}")
        resp = httpx.post(
            f"{API_BASE}/v1/inbox/email-reply",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "subject": f"Re: [{approval_id}]",
                "body": code
            },
            timeout=10
        )
        print(f"[Poller] Response: {resp.status_code} - {resp.text}")

        # 处理 409 - 审批已处理
        if resp.status_code == 409:
            # 返回一个表示已处理的状态
            return {"status": "already_processed", "detail": resp.json().get("detail")}

        return resp.json()
    except Exception as e:
        print(f"[Poller] API Error: {e}")
        return {}


def process_approval_with_note(approval_id: str, code: str, note: str) -> dict:
    """调用 API 处理带备注的审批"""
    body = f"{code} {note}" if note else code
    try:
        resp = httpx.post(
            f"{API_BASE}/v1/inbox/email-reply",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "subject": f"Re: [{approval_id}]",
                "body": body
            },
            timeout=10
        )
        return resp.json()
    except Exception:
        return {}


def handle_callback(callback_query):
    callback_id = callback_query["id"]
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    original_text = message.get("text", "")

    # 获取用户语言
    user = callback_query.get("from", {})
    user_id = str(user.get("id", ""))
    lang = get_lang(user.get("language_code"))

    # 安全检查：验证用户身份
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        answer_callback(callback_id, t("no_permission", lang))
        return

    if ":" not in data:
        answer_callback(callback_id, t("invalid", lang))
        return

    approval_id, code = data.split(":", 1)

    # 处理选择题选项点击
    if code.startswith("opt:"):
        option = code.split(":")[1]

        if option == "custom":
            # 直接弹出输入框，不显示额外提示
            answer_callback(callback_id, "")
            url = f"{TG_API}/sendMessage"
            httpx.post(url, data={
                "chat_id": chat_id,
                "text": f"📝 <code>{approval_id}</code>",
                "parse_mode": "HTML",
                "reply_markup": json.dumps({"force_reply": True, "selective": True, "input_field_placeholder": t("enter_custom", lang)})
            })
            return

        result = process_approval_with_note(approval_id, "4", option)
        status = result.get("status", "unknown")

        if status in ("approved", "denied"):
            answer_callback(callback_id, f"{t('selected', lang)}: {option}")
            new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n✅ <b>{t('selected', lang)}: {option}</b>"
            edit_message(chat_id, message_id, new_text)
        else:
            answer_callback(callback_id, f"{t('failed', lang)}: {status}")
        return

    # 处理「批准+备注」的提示
    if ":prompt" in data:
        parts = data.split(":")
        approval_id = parts[0]
        answer_callback(callback_id, t("reply_below", lang))
        url = f"{TG_API}/sendMessage"
        httpx.post(url, data={
            "chat_id": chat_id,
            "text": f"📝 {t('enter_note', lang)}:\n\nApproval ID: <code>{approval_id}</code>",
            "parse_mode": "HTML",
            "reply_markup": json.dumps({"force_reply": True, "selective": True})
        })
        return

    # 处理「修改后批准」的提示
    if code == "5" and ":prompt" in data:
        answer_callback(callback_id, t("reply_below", lang))
        url = f"{TG_API}/sendMessage"
        httpx.post(url, data={
            "chat_id": chat_id,
            "text": f"✏️ {t('enter_modify', lang)}:\n\nApproval ID: <code>{approval_id}</code>",
            "parse_mode": "HTML",
            "reply_markup": json.dumps({"force_reply": True, "selective": True})
        })
        return

    code_info = {
        "1": ("✅", "approve"),
        "2": ("✅", "approve_session"),
        "3": ("❌", "deny"),
        "6": ("♾️", "always_allow")
    }

    emoji, action_key = code_info.get(code, ("", code))
    result = process_approval(approval_id, code)
    status = result.get("status", "unknown")

    if status in ("approved", "denied"):
        status_text = t("approved", lang) if status == "approved" else t("denied", lang)
        answer_callback(callback_id, f"{emoji} {status_text}")
        status_emoji = "✅" if status == "approved" else "❌"
        new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n{status_emoji} <b>{status_text}</b>"
        edit_message(chat_id, message_id, new_text)
    elif status == "already_processed":
        # 审批已被处理（可能是重复点击或 hook 已处理）
        answer_callback(callback_id, "⚡ " + t("approved", lang))
        new_text = f"{original_text}\n\n━━━━━━━━━━━━━━━━━━━━\n⚡ <b>{t('approved', lang)}</b>"
        edit_message(chat_id, message_id, new_text)
    else:
        answer_callback(callback_id, f"{t('failed', lang)}: {status}")


def handle_text_reply(message):
    """处理文本回复（用于备注输入和选择题回答）"""
    text = message.get("text", "").strip()
    reply_to = message.get("reply_to_message", {})
    reply_text = reply_to.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    # 获取用户语言
    user = message.get("from", {})
    user_id = str(user.get("id", ""))
    lang = get_lang(user.get("language_code"))

    # 安全检查：验证用户身份
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        return

    approval_id = None
    match = re.search(r"(appr_[a-f0-9]+)", reply_text)
    if match:
        approval_id = match.group(1)

    if not approval_id:
        return

    # 使用 code 4 保存回复内容
    result = process_approval_with_note(approval_id, "4", text)

    if result.get("status") in ("approved", "denied"):
        url = f"{TG_API}/sendMessage"
        httpx.post(url, data={
            "chat_id": chat_id,
            "text": f"✅ {t('reply_received', lang)}\n\n{t('content', lang)}: {text}",
            "parse_mode": "HTML"
        })


def main():
    global last_update_id
    print("[Poller] Telegram 轮询已启动")

    while True:
        updates = get_updates()
        for update in updates:
            last_update_id = update["update_id"]

            if "callback_query" in update:
                handle_callback(update["callback_query"])
            elif "message" in update:
                msg = update["message"]
                if msg.get("reply_to_message"):
                    handle_text_reply(msg)


if __name__ == "__main__":
    main()
