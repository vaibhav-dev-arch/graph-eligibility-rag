#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -q -r requirements.txt
python3 app.py &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

sleep 5
python3 scripts/run_demo.py
