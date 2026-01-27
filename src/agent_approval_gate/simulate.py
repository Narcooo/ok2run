from fastapi import HTTPException
from sqlalchemy.orm import Session

from agent_approval_gate.decision import ParseError, parse_menu_reply
from agent_approval_gate.service import apply_decision, get_approval
from agent_approval_gate.utils import extract_approval_id, truncate_email_reply


def simulate_human_reply(
    db: Session, approval_id: str, reply_text: str, client_id: str | None = None
):
    approval = get_approval(db, approval_id)
    if client_id and approval.client_id != client_id:
        raise HTTPException(status_code=403, detail="approval client mismatch")
    try:
        decision = parse_menu_reply(reply_text)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return apply_decision(db, approval, decision)


def simulate_tg_reply(
    db: Session, approval_id: str, reply_text: str, client_id: str | None = None
):
    return simulate_human_reply(db, approval_id, reply_text, client_id=client_id)


def simulate_email_reply(
    db: Session, subject: str | None, body: str, client_id: str | None = None
):
    approval_id = extract_approval_id(subject or "") or extract_approval_id(body or "")
    if not approval_id:
        raise HTTPException(status_code=422, detail="approval_id not found")
    reply_text = truncate_email_reply(body)
    if not reply_text:
        raise HTTPException(status_code=422, detail="empty reply")
    return simulate_human_reply(db, approval_id, reply_text, client_id=client_id)
