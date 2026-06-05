#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$PROJECT_DIR/archive"
cd "$PROJECT_DIR"
source "$PROJECT_DIR/.venv/bin/activate"
options-put-call-report run --send-email >> "$PROJECT_DIR/archive/runner.log" 2>&1
