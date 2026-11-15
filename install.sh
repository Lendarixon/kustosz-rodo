#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 tools/setup_kustosz.py "$@"
python3 app.py
