from agent_approval_gate.auth import api_key_to_client_id
from agent_approval_gate.service import create_allow_rule


def test_create_and_get_approval(client):
    headers = {"Authorization": "Bearer test-key"}
    payload = {
        "session_id": "sess_123",
        "action_type": "exec_cmd",
        "title": "Run command",
        "preview": "rm -rf ./build && npm run build",
        "channel": "telegram",
        "target": {"tg_chat_id": "123"},
        "expires_in_sec": 600,
    }
    resp = client.post("/v1/approvals", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    approval_id = data["approval_id"]

    resp = client.get(f"/v1/approvals/{approval_id}", headers=headers)
    assert resp.status_code == 200
    status = resp.json()
    assert status["status"] == "pending"


def test_auto_approve_with_allow_rule(client, db_session):
    headers = {"Authorization": "Bearer test-key"}
    client_id = api_key_to_client_id("test-key")
    create_allow_rule(db_session, client_id, "write_file")

    payload = {
        "session_id": "sess_auto",
        "action_type": "write_file",
        "title": "Write file",
        "preview": "echo hi > /tmp/x",
        "channel": "telegram",
        "target": {"tg_chat_id": "123"},
        "expires_in_sec": 600,
    }
    resp = client.post("/v1/approvals", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["auto"] is True
    assert data["decision"]["code"] == "6"
