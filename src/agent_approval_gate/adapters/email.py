import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from agent_approval_gate.config import get_settings
from agent_approval_gate.decision import MENU_TEXT
from agent_approval_gate.utils import format_expires_at


@dataclass(frozen=True)
class EmailSendResult:
    subject: str
    to_addr: str


def build_email_subject(approval) -> str:
    return f"{approval.title} [{approval.approval_id}]"


def build_email_body(approval) -> str:
    expires_at = format_expires_at(approval.expires_at)
    return (
        f"{approval.preview}\n\n"
        f"Approval ID: {approval.approval_id}\n"
        f"Expires: {expires_at}\n\n"
        "Menu:\n"
        f"{MENU_TEXT}\n\n"
        "Reply with 1/2/3/4 <note>/5 <replacement>/6 in the first line."
    )


class EmailAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self.smtp_host = settings.email_smtp_host
        self.smtp_port = settings.email_smtp_port
        self.email_from = settings.email_from
        self.username = settings.email_username
        self.password = settings.email_password
        self.use_tls = settings.email_use_tls
        self.use_ssl = settings.email_use_ssl

    def send_approval(self, approval) -> EmailSendResult:
        subject = build_email_subject(approval)
        body = build_email_body(approval)
        to_addr = str(approval.target.get("email_to"))

        message = EmailMessage()
        message["From"] = self.email_from
        message["To"] = to_addr
        message["Subject"] = subject
        message.set_content(body)

        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
        else:
            smtp = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
        try:
            if self.use_tls and not self.use_ssl:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message)
        finally:
            smtp.quit()

        return EmailSendResult(subject=subject, to_addr=to_addr)
