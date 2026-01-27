from dataclasses import dataclass

MENU_LINES = [
    "1) Allow once",
    "2) Allow for this session",
    "3) Deny",
    "4) Allow once + add note (reply: 4 <text>)",
    "5) Modify then allow (reply: 5 <replacement>)",
    "6) Always allow this action type (until revoked)",
]

MENU_TEXT = "\n".join(MENU_LINES)


@dataclass(frozen=True)
class Decision:
    code: str
    note: str | None = None
    override: str | None = None


class ParseError(ValueError):
    pass


def parse_menu_reply(text: str) -> Decision:
    if text is None:
        raise ParseError("empty reply")
    stripped = text.strip()
    if not stripped:
        raise ParseError("empty reply")
    parts = stripped.split(maxsplit=1)
    code = parts[0]
    if code not in {"1", "2", "3", "4", "5", "6"}:
        raise ParseError("invalid code")
    payload = ""
    if len(parts) > 1:
        payload = parts[1].strip()
    if code in {"4", "5"} and not payload:
        raise ParseError("payload required")
    note = payload if code == "4" else None
    override = payload if code == "5" else None
    return Decision(code=code, note=note, override=override)
