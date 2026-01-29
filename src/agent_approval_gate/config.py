import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_keys: list[str]
    telegram_bot_token: str | None
    telegram_api_base: str
    telegram_mock: bool
    telegram_webhook_secret: str | None  # Secret token for webhook verification
    email_smtp_host: str
    email_smtp_port: int
    email_from: str
    email_username: str | None
    email_password: str | None
    email_use_tls: bool
    email_use_ssl: bool
    public_url: str | None  # 公网 URL，用于邮件按钮回调
    action_sign_key: str | None  # HMAC key for signing email action URLs


@lru_cache()
def get_settings() -> Settings:
    load_dotenv()
    api_keys_raw = os.getenv("APPROVAL_API_KEYS") or os.getenv("APPROVAL_API_KEY") or ""
    api_keys = [k.strip() for k in api_keys_raw.split(",") if k.strip()]

    telegram_mock = os.getenv("TELEGRAM_MOCK", "1").lower() in {"1", "true", "yes"}
    email_use_tls = os.getenv("EMAIL_USE_TLS", "0").lower() in {"1", "true", "yes"}
    email_use_ssl = os.getenv("EMAIL_USE_SSL", "0").lower() in {"1", "true", "yes"}

    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data.db"),
        api_keys=api_keys,
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_api_base=os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org"),
        telegram_mock=telegram_mock,
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET"),
        email_smtp_host=os.getenv("EMAIL_SMTP_HOST", "localhost"),
        email_smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "1025")),
        email_from=os.getenv("EMAIL_FROM", "approvals@example.com"),
        email_username=os.getenv("EMAIL_USERNAME"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_use_tls=email_use_tls,
        email_use_ssl=email_use_ssl,
        public_url=os.getenv("PUBLIC_URL"),  # e.g., https://your-vps.com
        action_sign_key=os.getenv("ACTION_SIGN_KEY"),  # For signing email action URLs
    )
