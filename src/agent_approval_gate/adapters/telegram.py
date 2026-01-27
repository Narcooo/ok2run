import json
from dataclasses import dataclass

import httpx

from agent_approval_gate.config import get_settings
from agent_approval_gate.decision import MENU_TEXT
from agent_approval_gate.utils import to_epoch


@dataclass(frozen=True)
class TelegramSendResult:
    message_text: str
    chat_id: str
    mock: bool


def build_telegram_message(approval) -> str:
    expires_at = to_epoch(approval.expires_at)
    return (
        f"{approval.title}\n\n"
        f"{approval.preview}\n\n"
        f"Approval ID: {approval.approval_id}\n"
        f"Expires: {expires_at}\n\n"
        "Menu:\n"
        f"{MENU_TEXT}\n\n"
        "Reply to this message with 1/2/3/4 <note>/5 <replacement>/6."
    )


def build_inline_keyboard(approval_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "1 Allow once", "callback_data": f"{approval_id}:1"},
                {"text": "2 Allow session", "callback_data": f"{approval_id}:2"},
            ],
            [
                {"text": "3 Deny", "callback_data": f"{approval_id}:3"},
                {"text": "6 Always allow", "callback_data": f"{approval_id}:6"},
            ],
        ]
    }


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
            "reply_markup": json.dumps(build_inline_keyboard(approval.approval_id)),
        }
        with httpx.Client(timeout=10) as client:
            response = client.post(url, data=payload)
            response.raise_for_status()
        return TelegramSendResult(message_text=message_text, chat_id=chat_id, mock=False)
