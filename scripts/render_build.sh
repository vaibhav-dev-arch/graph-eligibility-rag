#!/usr/bin/env bash
set -euo pipefail
# CPU-only PyTorch (~200MB). Do NOT reinstall torch from PyPI (pulls CUDA, OOM on 512Mi).
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
grep -v -E '^torch([>=<]|$)' requirements.txt > /tmp/requirements-no-torch.txt
pip install -r /tmp/requirements-no-torch.txt
