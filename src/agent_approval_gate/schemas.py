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
    options: list[str] | None = None  # 选择题选项


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


class QuestionOption(BaseModel):
    label: str
    description: str | None = None


class QuestionRequest(BaseModel):
    """Claude Code 风格的询问请求"""
    session_id: str
    question: str
    options: list[QuestionOption]
    allow_custom: bool = True  # 是否允许自定义输入
    channel: Literal["telegram", "email"]
    target: dict
    expires_in_sec: int = Field(default=600, ge=1)
