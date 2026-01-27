import datetime as dt

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON

from agent_approval_gate.database import Base


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True)
    approval_id = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(16), nullable=False, index=True)

    session_id = Column(String(128), nullable=False, index=True)
    action_type = Column(String(128), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    preview = Column(Text, nullable=False)

    decision_code = Column(String(4), nullable=True)
    decision_note = Column(Text, nullable=True)
    decision_override = Column(Text, nullable=True)

    channel = Column(String(16), nullable=False)
    target = Column(JSON, nullable=False)

    client_id = Column(String(64), nullable=False, index=True)
    allow_rule_applied = Column(String(64), nullable=True)


class AllowRule(Base):
    __tablename__ = "allow_rules"

    id = Column(Integer, primary_key=True)
    rule_id = Column(String(64), unique=True, index=True, nullable=False)
    client_id = Column(String(64), nullable=False, index=True)
    action_type = Column(String(128), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    __table_args__ = (UniqueConstraint("client_id", "action_type", name="uq_allow_rule"),)


class SessionAllow(Base):
    __tablename__ = "session_allows"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(128), nullable=False, index=True)
    client_id = Column(String(64), nullable=False, index=True)
    action_type = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=dt.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "session_id", "action_type", name="uq_session_allow"),
    )
