from fastapi import Depends, FastAPI, HTTPException

from agent_approval_gate.adapters import EmailAdapter, TelegramAdapter
from agent_approval_gate.auth import get_client_id
from agent_approval_gate.database import get_db, init_db
from agent_approval_gate.schemas import (
    ApprovalCreateRequest,
    ApprovalCreateResponse,
    ApprovalStatusResponse,
    EmailReplyIn,
)
from agent_approval_gate.service import (
    create_approval,
    expire_if_needed,
    get_approval,
    revoke_allow_rule,
    validate_target,
)
from agent_approval_gate.simulate import simulate_email_reply
from agent_approval_gate.utils import to_epoch

app = FastAPI(title="Agent Approval Gate")

telegram_adapter = TelegramAdapter()
email_adapter = EmailAdapter()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def decision_payload(approval):
    if not approval.decision_code:
        return None
    return {
        "code": approval.decision_code,
        "note": approval.decision_note,
        "override": approval.decision_override,
    }


@app.post("/v1/approvals", response_model=ApprovalCreateResponse)
def create_approval_endpoint(
    request: ApprovalCreateRequest,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    target = validate_target(request.channel, request.target)
    approval, auto = create_approval(
        db,
        session_id=request.session_id,
        action_type=request.action_type,
        title=request.title,
        preview=request.preview,
        channel=request.channel,
        target=target,
        expires_in_sec=request.expires_in_sec,
        client_id=client_id,
    )

    if not auto:
        if request.channel == "telegram":
            telegram_adapter.send_approval(approval)
        else:
            email_adapter.send_approval(approval)

    response = {
        "approval_id": approval.approval_id,
        "status": approval.status,
        "auto": auto,
    }
    if auto:
        response["decision"] = decision_payload(approval)
    else:
        response["expires_at"] = to_epoch(approval.expires_at)
    return response


@app.get("/v1/approvals/{approval_id}", response_model=ApprovalStatusResponse)
def get_approval_endpoint(
    approval_id: str,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    approval = get_approval(db, approval_id)
    if approval.client_id != client_id:
        raise HTTPException(status_code=404, detail="approval not found")
    approval = expire_if_needed(db, approval)

    response = {"status": approval.status}
    if approval.status == "pending":
        response["expires_at"] = to_epoch(approval.expires_at)
        return response

    response["expires_at"] = to_epoch(approval.expires_at)
    response["decision"] = decision_payload(approval)
    response["session_id"] = approval.session_id
    response["action_type"] = approval.action_type
    return response


@app.post("/v1/inbox/email-reply")
def email_reply_endpoint(
    payload: EmailReplyIn,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    approval = simulate_email_reply(db, payload.subject, payload.body, client_id=client_id)
    return {"status": approval.status, "approval_id": approval.approval_id}


@app.delete("/v1/allow-rules/{rule_id}")
def revoke_allow_rule_endpoint(
    rule_id: str,
    client_id: str = Depends(get_client_id),
    db=Depends(get_db),
):
    rule = revoke_allow_rule(db, rule_id, client_id=client_id)
    return {
        "rule_id": rule.rule_id,
        "status": "revoked",
        "client_id": client_id,
        "action_type": rule.action_type,
    }
