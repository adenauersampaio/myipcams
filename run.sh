#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual .venv..."
    python3 -m venv .venv
    .venv/bin/pip install -e .
fi

exec .venv/bin/python3 -m myipcams.main "$@"
