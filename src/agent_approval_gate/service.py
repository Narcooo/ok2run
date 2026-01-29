import datetime as dt
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_approval_gate.decision import Decision
from agent_approval_gate.models import AllowRule, Approval, SessionAllow


def utcnow() -> dt.datetime:
    return dt.datetime.utcnow()


def make_approval_id() -> str:
    return f"appr_{uuid.uuid4().hex}"  # Full 32 hex chars (128 bits)


def make_rule_id() -> str:
    return f"rule_{uuid.uuid4().hex}"  # Full 32 hex chars (128 bits)


def validate_target(channel: str, target: dict) -> dict:
    if channel == "telegram":
        chat_id = target.get("tg_chat_id") if target else None
        if not chat_id:
            raise HTTPException(status_code=422, detail="target.tg_chat_id required")
        return {"tg_chat_id": str(chat_id)}
    if channel == "email":
        email_to = target.get("email_to") if target else None
        if not email_to:
            raise HTTPException(status_code=422, detail="target.email_to required")
        return {"email_to": str(email_to)}
    raise HTTPException(status_code=422, detail="invalid channel")


def get_allow_rule(db: Session, client_id: str, action_type: str) -> AllowRule | None:
    stmt = select(AllowRule).where(
        AllowRule.client_id == client_id,
        AllowRule.action_type == action_type,
        AllowRule.enabled.is_(True),
    )
    return db.execute(stmt).scalars().first()


def get_allow_rule_any(db: Session, client_id: str, action_type: str) -> AllowRule | None:
    stmt = select(AllowRule).where(
        AllowRule.client_id == client_id,
        AllowRule.action_type == action_type,
    )
    return db.execute(stmt).scalars().first()


def get_session_allow(
    db: Session, client_id: str, session_id: str, action_type: str
) -> SessionAllow | None:
    stmt = select(SessionAllow).where(
        SessionAllow.client_id == client_id,
        SessionAllow.session_id == session_id,
        SessionAllow.action_type == action_type,
    )
    return db.execute(stmt).scalars().first()


def create_session_allow(
    db: Session, client_id: str, session_id: str, action_type: str
) -> SessionAllow:
    existing = get_session_allow(db, client_id, session_id, action_type)
    if existing:
        return existing
    record = SessionAllow(
        client_id=client_id,
        session_id=session_id,
        action_type=action_type,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_allow_rule(db: Session, client_id: str, action_type: str) -> AllowRule:
    existing = get_allow_rule_any(db, client_id, action_type)
    if existing:
        if not existing.enabled:
            existing.enabled = True
            db.commit()
        return existing
    rule = AllowRule(
        rule_id=make_rule_id(),
        client_id=client_id,
        action_type=action_type,
        enabled=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def create_approval(
    db: Session,
    *,
    session_id: str,
    action_type: str,
    title: str,
    preview: str,
    channel: str,
    target: dict,
    expires_in_sec: int,
    client_id: str,
) -> tuple[Approval, bool]:
    now = utcnow()
    expires_at = now + dt.timedelta(seconds=expires_in_sec)

    allow_rule = get_allow_rule(db, client_id, action_type)
    session_allow = get_session_allow(db, client_id, session_id, action_type)

    approval = Approval(
        approval_id=make_approval_id(),
        created_at=now,
        expires_at=expires_at,
        status="pending",
        session_id=session_id,
        action_type=action_type,
        title=title,
        preview=preview,
        channel=channel,
        target=target,
        client_id=client_id,
    )

    auto = False
    if allow_rule:
        approval.status = "approved"
        approval.decision_code = "6"
        approval.allow_rule_applied = allow_rule.rule_id
        auto = True
    elif session_allow:
        approval.status = "approved"
        approval.decision_code = "2"
        auto = True

    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval, auto


def expire_if_needed(db: Session, approval: Approval) -> Approval:
    if approval.status == "pending" and approval.expires_at <= utcnow():
        approval.status = "expired"
        db.commit()
        db.refresh(approval)
    return approval


def get_approval(db: Session, approval_id: str) -> Approval:
    stmt = select(Approval).where(Approval.approval_id == approval_id)
    approval = db.execute(stmt).scalars().first()
    if not approval:
        raise HTTPException(status_code=404, detail="approval not found")
    return approval


def get_approval_no_check(db: Session, approval_id: str) -> Approval:
    """获取审批记录（不检查 client_id，用于邮件按钮回调）"""
    stmt = select(Approval).where(Approval.approval_id == approval_id)
    approval = db.execute(stmt).scalars().first()
    if not approval:
        raise HTTPException(status_code=404, detail="approval not found")
    return approval


def apply_decision(db: Session, approval: Approval, decision: Decision) -> Approval:
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="approval not pending")
    if approval.expires_at <= utcnow():
        approval.status = "expired"
        db.commit()
        db.refresh(approval)
        raise HTTPException(status_code=410, detail="approval expired")

    approval.decision_code = decision.code
    approval.decision_note = decision.note
    approval.decision_override = decision.override

    if decision.code == "3":
        approval.status = "denied"
    else:
        approval.status = "approved"

    if decision.code == "2":
        create_session_allow(db, approval.client_id, approval.session_id, approval.action_type)
    if decision.code == "6":
        rule = create_allow_rule(db, approval.client_id, approval.action_type)
        approval.allow_rule_applied = rule.rule_id

    db.commit()
    db.refresh(approval)
    return approval


def revoke_allow_rule(db: Session, rule_id: str, client_id: str | None = None) -> AllowRule:
    stmt = select(AllowRule).where(AllowRule.rule_id == rule_id)
    rule = db.execute(stmt).scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    if client_id and rule.client_id != client_id:
        raise HTTPException(status_code=404, detail="rule not found")
    rule.enabled = False
    db.commit()
    db.refresh(rule)
    return rule
