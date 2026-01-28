import calendar
import datetime as dt
import os
import re

APPROVAL_ID_RE = re.compile(r"(appr_[A-Za-z0-9]+)")


def to_epoch(timestamp: dt.datetime) -> int:
    if timestamp.tzinfo is None:
        return int(calendar.timegm(timestamp.timetuple()))
    return int(timestamp.astimezone(dt.timezone.utc).timestamp())


def format_expires_at(timestamp: dt.datetime, timezone_name: str | None = None) -> str:
    """Format expiration time in human-readable format with timezone."""
    if timezone_name is None:
        timezone_name = os.getenv("DISPLAY_TIMEZONE", "Asia/Shanghai")

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = dt.timezone(dt.timedelta(hours=8))  # fallback to UTC+8
        timezone_name = "UTC+8"

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)

    local_time = timestamp.astimezone(tz)
    formatted = local_time.strftime("%Y-%m-%d %H:%M:%S")
    return f"{formatted} ({timezone_name})"


def extract_approval_id(text: str) -> str | None:
    if not text:
        return None
    match = APPROVAL_ID_RE.search(text)
    if not match:
        return None
    return match.group(1)


def truncate_email_reply(body: str) -> str:
    if not body:
        return ""
    lines = body.splitlines()
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            break
        if stripped.lower().startswith("on ") and stripped.lower().endswith("wrote:"):
            break
        if stripped.startswith("-----Original Message-----"):
            break
        if stripped in {"--", "-- ", "__"}:
            break
        if stripped.lower().startswith("sent from my"):
            break
        if stripped.startswith("From:") and "@" in stripped:
            break
        if stripped.startswith("Subject:"):
            break
        if stripped.startswith("To:"):
            break
        if stripped.startswith("Cc:"):
            break
        kept.append(line)
    return "\n".join(kept).strip()
