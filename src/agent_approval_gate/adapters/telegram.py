import html
import json
from dataclasses import dataclass

import httpx

from agent_approval_gate.config import get_settings
from agent_approval_gate.decision import MENU_TEXT
from agent_approval_gate.i18n import t
from agent_approval_gate.utils import format_expires_at


@dataclass(frozen=True)
class TelegramSendResult:
    message_text: str
    chat_id: str
    mock: bool


def build_telegram_message(approval, lang: str = None) -> str:
    expires_at = format_expires_at(approval.expires_at)
    # Escape HTML entities to prevent injection
    safe_title = html.escape(approval.title or "")
    safe_preview = html.escape(approval.preview or "")
    return (
        f"<b>🔔 {safe_title}</b>\n\n"
        f"<pre>{safe_preview}</pre>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <code>{approval.approval_id}</code>\n"
        f"⏰ {expires_at}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<i>{t('click_button', lang)}</i>"
    )


def build_inline_keyboard(approval_id: str, lang: str = None) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": f"✅ {t('approve', lang)}", "callback_data": f"{approval_id}:1"},
                {"text": f"✅ {t('approve_session', lang)}", "callback_data": f"{approval_id}:2"},
            ],
            [
                {"text": f"❌ {t('deny', lang)}", "callback_data": f"{approval_id}:3"},
                {"text": f"♾️ {t('always_allow', lang)}", "callback_data": f"{approval_id}:6"},
            ],
        ]
    }


def build_question_keyboard(approval_id: str, options: list, lang: str = None) -> dict:
    """构建选择题按钮键盘"""
    buttons = []
    for i, opt in enumerate(options):
        letter = chr(65 + i)  # A, B, C, D...
        # 截断过长的选项文本
        display_text = f"{letter}) {opt[:20]}" if len(opt) > 20 else f"{letter}) {opt}"
        buttons.append({
            "text": display_text,
            "callback_data": f"{approval_id}:opt:{letter}"
        })
    # 每行最多2个按钮
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    # 添加自定义回复按钮
    rows.append([{"text": f"📝 {t('custom_reply', lang)}", "callback_data": f"{approval_id}:opt:custom"}])
    return {"inline_keyboard": rows}


class TelegramAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token
        self.api_base = settings.telegram_api_base.rstrip("/")
        self.mock = settings.telegram_mock

    def send_approval(self, approval) -> TelegramSendResult:
        message_text = build_telegram_message(approval)
        chat_id = str(approval.target.get("tg_chat_id"))
        if self.mock or not self.bot_token:
            return TelegramSendResult(message_text=message_text, chat_id=chat_id, mock=True)

        url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(build_inline_keyboard(approval.approval_id)),
        }
        with httpx.Client(timeout=10) as client:
            response = client.post(url, data=payload)
            response.raise_for_status()
        return TelegramSendResult(message_text=message_text, chat_id=chat_id, mock=False)

    def send_question(self, approval, options: list) -> TelegramSendResult:
        """发送选择题消息"""
        expires_at = format_expires_at(approval.expires_at)
        # Escape HTML entities to prevent injection
        safe_title = html.escape(approval.title or "")
        safe_options = [html.escape(opt) for opt in options]
        # 构建选项文本
        options_text = "\n".join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(safe_options)])
        message_text = (
            f"<b>❓ {safe_title}</b>\n\n"
            f"{options_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <code>{approval.approval_id}</code>\n"
            f"⏰ {expires_at}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<i>{t('click_to_select')}</i>"
        )
        chat_id = str(approval.target.get("tg_chat_id"))
        if self.mock or not self.bot_token:
            return TelegramSendResult(message_text=message_text, chat_id=chat_id, mock=True)

        url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(build_question_keyboard(approval.approval_id, options)),
        }
        with httpx.Client(timeout=10) as client:
            response = client.post(url, data=payload)
            response.raise_for_status()
        return TelegramSendResult(message_text=message_text, chat_id=chat_id, mock=False)
