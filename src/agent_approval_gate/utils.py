import calendar
import datetime as dt
import re

APPROVAL_ID_RE = re.compile(r"(appr_[A-Za-z0-9]+)")


def to_epoch(timestamp: dt.datetime) -> int:
    if timestamp.tzinfo is None:
        return int(calendar.timegm(timestamp.timetuple()))
    return int(timestamp.astimezone(dt.timezone.utc).timestamp())


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
