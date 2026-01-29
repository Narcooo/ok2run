import hmac
import hashlib
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

from agent_approval_gate.config import get_settings
from agent_approval_gate.decision import MENU_TEXT
from agent_approval_gate.utils import format_expires_at


def generate_action_signature(approval_id: str, action: str, sign_key: str) -> str:
    """Generate HMAC signature for action URL"""
    message = f"{approval_id}:{action}".encode()
    return hmac.new(sign_key.encode(), message, hashlib.sha256).hexdigest()[:16]


def verify_action_signature(approval_id: str, action: str, signature: str, sign_key: str) -> bool:
    """Verify HMAC signature for action URL"""
    expected = generate_action_signature(approval_id, action, sign_key)
    return hmac.compare_digest(signature, expected)


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


def _button_style(color: str) -> str:
    return f"""display: inline-block; padding: 12px 24px; margin: 6px;
        background-color: {color}; color: white; text-decoration: none;
        border-radius: 8px; font-weight: bold; font-size: 14px;"""


def build_html_body(approval, from_addr: str, options: list | None = None) -> str:
    """构建 HTML 邮件正文，包含可点击按钮"""
    settings = get_settings()
    public_url = settings.public_url
    sign_key = settings.action_sign_key
    expires_at = format_expires_at(approval.expires_at)
    approval_id = approval.approval_id

    # 如果有公网 URL，使用 HTTP 链接（一键审批）
    # 否则使用 mailto 链接（需要手动发送）
    use_http = bool(public_url)

    def make_action_url(action: str) -> str:
        """Generate action URL with optional signature"""
        base_url = f"{public_url}/v1/action/{approval_id}/{action}"
        if sign_key:
            sig = generate_action_signature(approval_id, action, sign_key)
            return f"{base_url}?sig={sig}"
        return base_url

    button_html = ""

    if options:
        # ABCD 选项模式
        for i, opt in enumerate(options):
            letter = chr(65 + i)  # A, B, C, D
            label = f"{letter}) {opt[:30]}" if len(opt) > 30 else f"{letter}) {opt}"
            if use_http:
                url = make_action_url(f"option_{letter}")
            else:
                subject = f"Re: {approval.title} [{approval_id}]"
                url = f"mailto:{from_addr}?subject={quote(subject)}&body={quote(letter)}"
            button_html += f'<a href="{url}" style="{_button_style("#3b82f6")}">{label}</a>\n'
        # 添加自定义输入按钮
        if use_http:
            custom_url = make_action_url("custom_form")
            button_html += f'<a href="{custom_url}" style="{_button_style("#6b7280")}">📝 Custom</a>\n'
    else:
        # 标准审批模式：批准、Session批准、拒绝、永久批准
        buttons = [
            ("✅ Approve", "approve", "#22c55e"),
            ("✅ Session", "session", "#10b981"),
            ("❌ Deny", "deny", "#ef4444"),
            ("♾️ Always", "always", "#8b5cf6"),
        ]
        for label, action, color in buttons:
            if use_http:
                url = make_action_url(action)
            else:
                subject = f"Re: {approval.title} [{approval_id}]"
                code = {"approve": "1", "session": "2", "deny": "3", "always": "6"}[action]
                url = f"mailto:{from_addr}?subject={quote(subject)}&body={quote(code)}"
            button_html += f'<a href="{url}" style="{_button_style(color)}">{label}</a>\n'

    # 转义 preview
    preview_html = (approval.preview or "").replace("&", "&amp;")
    preview_html = preview_html.replace("<", "&lt;").replace(">", "&gt;")
    preview_html = preview_html.replace("\n", "<br>")

    mode_hint = "Click a button to respond instantly." if use_http else "Click a button to open your email client."

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             background-color: #f3f4f6; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white;
                border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 24px; color: white;">
            <h1 style="margin: 0; font-size: 20px;">🔐 {"Question" if options else "Approval Required"}</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">{approval.title}</p>
        </div>
        <div style="padding: 24px;">
            <div style="background-color: #f8fafc; border-left: 4px solid #667eea;
                        padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 20px;">
                <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;
                           font-family: 'SF Mono', Monaco, monospace; font-size: 13px;
                           color: #334155; line-height: 1.5;">{preview_html}</pre>
            </div>
            <div style="color: #64748b; font-size: 13px; margin-bottom: 20px;">
                <p style="margin: 4px 0;"><strong>ID:</strong> <code style="background: #e2e8f0;
                   padding: 2px 6px; border-radius: 4px;">{approval_id}</code></p>
                <p style="margin: 4px 0;"><strong>Expires:</strong> {expires_at}</p>
            </div>
            <div style="text-align: center; padding: 16px 0;">
                {button_html}
            </div>
            <p style="color: #94a3b8; font-size: 12px; text-align: center; margin-top: 20px;">
                {mode_hint}
            </p>
        </div>
        <div style="background-color: #f8fafc; padding: 16px; text-align: center;
                    border-top: 1px solid #e2e8f0;">
            <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                Powered by Agent Approval Gate
            </p>
        </div>
    </div>
</body>
</html>'''
    return html


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

    def _send(self, approval, options: list | None = None) -> EmailSendResult:
        subject = build_email_subject(approval)
        text_body = build_email_body(approval)
        to_addr = str(approval.target.get("email_to"))

        message = MIMEMultipart("alternative")
        message["From"] = self.email_from
        message["To"] = to_addr
        message["Subject"] = subject

        text_part = MIMEText(text_body, "plain", "utf-8")
        message.attach(text_part)

        html_body = build_html_body(approval, self.email_from, options)
        html_part = MIMEText(html_body, "html", "utf-8")
        message.attach(html_part)

        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=60)
        else:
            smtp = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=60)
        try:
            if self.use_tls and not self.use_ssl:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message)
        finally:
            smtp.quit()

        return EmailSendResult(subject=subject, to_addr=to_addr)

    def send_approval(self, approval) -> EmailSendResult:
        return self._send(approval)

    def send_question(self, approval, options: list) -> EmailSendResult:
        return self._send(approval, options)
