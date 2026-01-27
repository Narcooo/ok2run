from agent_approval_gate.simulate import simulate_human_reply


def test_simulate_reply_flow(client, db_session):
    headers = {"Authorization": "Bearer test-key"}
    payload = {
        "session_id": "sess_999",
        "action_type": "exec_cmd",
        "title": "Run command",
        "preview": "echo hello",
        "channel": "telegram",
        "target": {"tg_chat_id": "123"},
        "expires_in_sec": 600,
    }
    resp = client.post("/v1/approvals", json=payload, headers=headers)
    approval_id = resp.json()["approval_id"]

    simulate_human_reply(db_session, approval_id, "4 please add logs")

    resp = client.get(f"/v1/approvals/{approval_id}", headers=headers)
    data = resp.json()
    assert data["status"] == "approved"
    assert data["decision"]["code"] == "4"
    assert data["decision"]["note"] == "please add logs"
