#!/bin/bash
# 启动 Agent Approval Gate 服务

cd "$(dirname "$0")/.."

# 停止现有进程
pkill -f "uvicorn src.agent_approval_gate.main:app" 2>/dev/null
pkill -f "telegram_poller.py" 2>/dev/null
sleep 1

# 启动 API 服务
echo "[Start] Starting API server..."
nohup python -m uvicorn src.agent_approval_gate.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
API_PID=$!
echo "[Start] API PID: $API_PID"

# 等待 API 启动
sleep 2

# 检查 API 是否启动成功
if curl -sS http://127.0.0.1:8000/v1/approvals -X POST \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"health","action_type":"health","title":"Health Check","preview":"startup","channel":"telegram","target":{"tg_chat_id":"5103672082"},"expires_in_sec":5}' > /dev/null 2>&1; then
  echo "[Start] API server started successfully"
else
  echo "[Start] ERROR: API server failed to start"
  exit 1
fi

# 启动 Telegram Poller
echo "[Start] Starting Telegram poller..."
nohup python -u scripts/telegram_poller.py > telegram_poller.log 2>&1 &
POLLER_PID=$!
echo "[Start] Poller PID: $POLLER_PID"

sleep 1

echo ""
echo "=== Services Started ==="
echo "API:    http://127.0.0.1:8000"
echo "Logs:   api.log, telegram_poller.log"
echo ""
echo "To stop: pkill -f uvicorn; pkill -f telegram_poller"
