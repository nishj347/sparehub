#!/usr/bin/env bash
# ==============================================================================
# gen-secret.sh: Generates a cryptographically secure 32+ char SECRET_KEY.
#
# Usage:
#   ./scripts/deploy/gen-secret.sh
# ==============================================================================
set -euo pipefail

if command -v python3 >/dev/null 2>&1 && python3 -c "import secrets" >/dev/null 2>&1; then
    python3 -c "import secrets; print(secrets.token_urlsafe(48))"
elif command -v python >/dev/null 2>&1 && python -c "import secrets" >/dev/null 2>&1; then
    python -c "import secrets; print(secrets.token_urlsafe(48))"
elif command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
else
    # Fallback to /dev/urandom if available
    LC_ALL=C tr -dc 'A-Za-z0-9_-' </dev/urandom | head -c 48
    echo ""
fi
