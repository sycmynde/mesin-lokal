#!/usr/bin/env bash
# One-click restore for mesin AI project (Termux)
# Usage: bash setup.sh   (run as non-root in Termux)
set -euo pipefail

echo "=== [1/4] Termux packages ==="
xargs -a packages.txt pkg install -y 2>/dev/null || true

echo "=== [2/4] Python deps ==="
pip install -r requirements.txt

echo "=== [3/4] Node deps ==="
npm install

echo "=== [4/4] Done ==="
echo "Model .gguf files must be downloaded separately into ~/models"
echo "Then run: bash start.sh (or your entrypoint)"
