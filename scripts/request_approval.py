import argparse
import json
import os
import sys
import urllib.request


def request(method: str, url: str, api_key: str, payload: dict | None = None):
    headers = {"Authorization": f"Bearer {api_key}"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, (json.loads(body) if body else None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an approval request.")
    parser.add_argument("--base-url", default=os.getenv("APPROVAL_GATE_URL", "http://localhost:8000"))
    parser.add_argument("--api-key", default=os.getenv("APPROVAL_API_KEY"))
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--action-type", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--preview", required=True)
    parser.add_argument("--channel", choices=["email", "telegram"], required=True)
    parser.add_argument("--email-to")
    parser.add_argument("--tg-chat-id")
    parser.add_argument("--expires-in-sec", type=int, default=600)

    args = parser.parse_args()
    if not args.api_key:
        print("Missing API key: set --api-key or APPROVAL_API_KEY", file=sys.stderr)
        return 2

    if args.channel == "email" and not args.email_to:
        print("--email-to is required for email channel", file=sys.stderr)
        return 2
    if args.channel == "telegram" and not args.tg_chat_id:
        print("--tg-chat-id is required for telegram channel", file=sys.stderr)
        return 2

    target = {"email_to": args.email_to} if args.channel == "email" else {"tg_chat_id": args.tg_chat_id}

    payload = {
        "session_id": args.session_id,
        "action_type": args.action_type,
        "title": args.title,
        "preview": args.preview,
        "channel": args.channel,
        "target": target,
        "expires_in_sec": args.expires_in_sec,
    }

    url = args.base_url.rstrip("/") + "/v1/approvals"
    status, data = request("POST", url, args.api_key, payload)
    print(json.dumps({"status": status, "response": data}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
