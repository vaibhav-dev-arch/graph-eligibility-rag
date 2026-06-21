#!/usr/bin/env bash
set -euo pipefail
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
