from typing import Literal

from pydantic import BaseModel, Field


class ApprovalCreateRequest(BaseModel):
    session_id: str
    action_type: str
    title: str
    preview: str
    channel: Literal["telegram", "email"]
    target: dict
    expires_in_sec: int = Field(default=600, ge=1)


class DecisionModel(BaseModel):
    code: str
    note: str | None = None
    override: str | None = None


class ApprovalCreateResponse(BaseModel):
    approval_id: str
    status: str
    auto: bool
    expires_at: int | None = None
    decision: DecisionModel | None = None


class ApprovalStatusResponse(BaseModel):
    status: str
    expires_at: int | None = None
    decision: DecisionModel | None = None
    session_id: str | None = None
    action_type: str | None = None


class EmailReplyIn(BaseModel):
    subject: str | None = None
    body: str
