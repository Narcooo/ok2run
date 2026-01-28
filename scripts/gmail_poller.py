#!/usr/bin/env python3
"""
Gmail 轮询脚本：通过 IMAP 读取邮件回复并处理审批
"""

import email
import imaplib
import os
import re
import time

import httpx

# 配置
IMAP_HOST = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("EMAIL_IMAP_PORT", "993"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "dev-key")

# 允许的发件人邮箱（只有这些邮箱的回复会被处理）
# 格式：逗号分隔，如 "admin@example.com,user@example.com"
ALLOWED_SENDERS = set(filter(None, os.getenv("ALLOWED_SENDERS", "").split(",")))

# 匹配 approval_id 的正则
APPROVAL_ID_RE = re.compile(r"(appr_[a-f0-9]+)")


def connect_imap():
    """连接到 IMAP 服务器"""
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    return mail


def get_unread_emails(mail):
    """获取未读的审批相关邮件（主题包含 appr_）"""
    mail.select("INBOX")
    # 只搜索主题包含 appr_ 的未读邮件
    _, message_numbers = mail.search(None, 'UNSEEN', 'SUBJECT', 'appr_')
    return message_numbers[0].split()


def parse_email(mail, num):
    """解析邮件内容"""
    _, msg_data = mail.fetch(num, "(RFC822)")
    email_body = msg_data[0][1]
    msg = email.message_from_bytes(email_body)

    subject = msg["Subject"] or ""
    from_addr = msg["From"] or ""

    # 获取邮件正文
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

    return subject, from_addr, body


def extract_approval_id(text: str) -> str | None:
    """从文本中提取 approval_id"""
    match = APPROVAL_ID_RE.search(text)
    return match.group(1) if match else None


def extract_reply_code(body: str) -> str | None:
    """从邮件正文中提取回复代码（第一行）"""
    lines = body.strip().split("\n")
    if lines:
        first_line = lines[0].strip()
        # 检查是否是有效的回复代码
        if first_line and first_line[0] in "123456":
            return first_line
    return None


def process_approval(approval_id: str, reply_code: str) -> dict:
    """调用 API 处理审批"""
    try:
        resp = httpx.post(
            f"{API_BASE}/v1/inbox/email-reply",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "subject": f"Re: [{approval_id}]",
                "body": reply_code
            },
            timeout=10
        )
        return resp.json()
    except Exception as e:
        print(f"[Gmail] API error: {e}")
        return {}


def extract_email_address(from_header: str) -> str:
    """从 From 头部提取纯邮箱地址"""
    # 处理格式如 "Name <email@example.com>" 或 "email@example.com"
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).lower()
    return from_header.strip().lower()


def process_email(mail, num):
    """处理单封邮件"""
    subject, from_addr, body = parse_email(mail, num)

    # 安全检查：验证发件人
    sender_email = extract_email_address(from_addr)
    if ALLOWED_SENDERS and sender_email not in ALLOWED_SENDERS:
        print(f"[Gmail] Ignored: sender {sender_email} not in whitelist")
        return

    # 从主题或正文中提取 approval_id
    approval_id = extract_approval_id(subject) or extract_approval_id(body)

    if not approval_id:
        print(f"[Gmail] No approval_id found in email from {from_addr}")
        return

    # 提取回复代码
    reply_code = extract_reply_code(body)

    if not reply_code:
        print(f"[Gmail] No valid reply code in email for {approval_id}")
        return

    print(f"[Gmail] Processing: {approval_id} -> {reply_code}")

    result = process_approval(approval_id, reply_code)
    status = result.get("status", "unknown")

    print(f"[Gmail] Result: {approval_id} -> {status}")


def main():
    print("[Gmail] Gmail 轮询已启动")
    print(f"[Gmail] IMAP: {IMAP_HOST}:{IMAP_PORT}")
    print(f"[Gmail] User: {EMAIL_USERNAME}")
    if ALLOWED_SENDERS:
        print(f"[Gmail] Allowed senders: {ALLOWED_SENDERS}")
    else:
        print("[Gmail] WARNING: No sender whitelist configured (ALLOWED_SENDERS)")

    while True:
        try:
            mail = connect_imap()
            unread = get_unread_emails(mail)

            if unread:
                print(f"[Gmail] Found {len(unread)} unread emails")
                for num in unread:
                    process_email(mail, num)
                    # 标记为已读
                    mail.store(num, "+FLAGS", "\\Seen")

            mail.logout()
        except Exception as e:
            print(f"[Gmail] Error: {e}")

        # 每 30 秒检查一次
        time.sleep(30)


if __name__ == "__main__":
    main()
