#!/usr/bin/env bash
#
# Run mousemaster-gw directly from source.
#
# Usage:
#   ./start.sh              # normal mode
#   ./start.sh --verbose    # debug logging
#   ./start.sh --no-check   # skip requirements check
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

exec python3 main.py "$@"