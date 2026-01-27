import os

os.environ.setdefault("APPROVAL_API_KEY", "demo-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./e2e.db")
os.environ.setdefault("TELEGRAM_MOCK", "1")

from agent_approval_gate.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient

from agent_approval_gate.database import SessionLocal, init_db
from agent_approval_gate.main import app
from agent_approval_gate.simulate import simulate_human_reply


def main() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Authorization": "Bearer demo-key"}

    payload = {
        "session_id": "sess_e2e",
        "action_type": "exec_cmd",
        "title": "Run command",
        "preview": "npm test",
        "channel": "telegram",
        "target": {"tg_chat_id": "123"},
        "expires_in_sec": 600,
    }
    resp = client.post("/v1/approvals", json=payload, headers=headers)
    resp.raise_for_status()
    approval_id = resp.json()["approval_id"]

    db = SessionLocal()
    try:
        simulate_human_reply(db, approval_id, "5 npm test -- --runInBand")
    finally:
        db.close()

    resp = client.get(f"/v1/approvals/{approval_id}", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    assert data["status"] == "approved"
    assert data["decision"]["code"] == "5"
    assert data["decision"]["override"] == "npm test -- --runInBand"

    print("e2e demo passed")


if __name__ == "__main__":
    main()
