import datetime as dt
import errno

import aiosmtpd.controller as smtp_controller
from aiosmtpd.controller import Controller
import pytest

from agent_approval_gate.adapters.email import EmailAdapter
from agent_approval_gate.config import get_settings
from agent_approval_gate.models import Approval


class MailSink:
    def __init__(self) -> None:
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope)
        return "250 OK"


def test_email_adapter_sends_mail(monkeypatch):
    handler = MailSink()
    monkeypatch.setattr(smtp_controller, "get_localhost", lambda: "127.0.0.1")
    controller = Controller(handler, hostname="127.0.0.1", port=8026)
    try:
        controller.start()
    except OSError as exc:
        controller.stop()
        if exc.errno == errno.EPERM:
            pytest.skip("Local SMTP server bind not permitted in this environment")
        raise
    try:
        monkeypatch.setenv("EMAIL_SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("EMAIL_SMTP_PORT", "8026")
        monkeypatch.setenv("EMAIL_FROM", "approvals@example.com")
        get_settings.cache_clear()

        adapter = EmailAdapter()
        approval = Approval(
            approval_id="appr_test123",
            created_at=dt.datetime.utcnow(),
            expires_at=dt.datetime.utcnow(),
            status="pending",
            session_id="sess1",
            action_type="send_message",
            title="Test Approval",
            preview="Send message to user",
            channel="email",
            target={"email_to": "user@example.com"},
            client_id="client1",
        )
        adapter.send_approval(approval)
        assert handler.messages
    finally:
        controller.stop()
