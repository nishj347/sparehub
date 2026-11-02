#!/usr/bin/env bash
# ==============================================================================
# neon-url.sh: Converts Neon PostgreSQL URL to postgresql+psycopg:// scheme
#              and ensures sslmode=require for psycopg v3 compatibility.
#
# Usage:
#   ./scripts/deploy/neon-url.sh "postgresql://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require"
#   # Or run without arguments to be prompted interactively
# ==============================================================================
set -euo pipefail

RAW_URL="${1:-}"

if [[ -z "$RAW_URL" ]]; then
    read -r -p "Enter Neon PostgreSQL connection string: " RAW_URL
fi

# Trim whitespace
RAW_URL="$(echo "$RAW_URL" | xargs)"

if [[ -z "$RAW_URL" ]]; then
    echo "Error: No URL provided." >&2
    exit 1
fi

# Use Python for robust URL parsing if available
if command -v python3 >/dev/null 2>&1 && python3 -c "import urllib.parse" >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1 && python -c "import urllib.parse" >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    PYTHON_CMD=""
fi

if [[ -n "$PYTHON_CMD" ]]; then
    "$PYTHON_CMD" - "$RAW_URL" << 'EOF'
import sys
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

raw = sys.argv[1].strip()
if raw.startswith("postgres://"):
    raw = "postgresql://" + raw[len("postgres://"):]
elif not (raw.startswith("postgresql://") or raw.startswith("postgresql+psycopg://")):
    raw = "postgresql://" + raw

parsed = urlparse(raw)
query_dict = dict(parse_qsl(parsed.query, keep_blank_values=True))
query_dict["sslmode"] = "require"
new_query = urlencode(query_dict)

converted = urlunparse((
    "postgresql+psycopg",
    parsed.netloc,
    parsed.path,
    parsed.params,
    new_query,
    ""
))
print(converted)
EOF
else
    # Pure bash fallback: replace scheme and ensure sslmode=require
    CLEANED="$RAW_URL"
    if [[ "$CLEANED" =~ ^postgres://(.*)$ ]]; then
        CLEANED="postgresql+psycopg://${BASH_REMATCH[1]}"
    elif [[ "$CLEANED" =~ ^postgresql://(.*)$ ]]; then
        CLEANED="postgresql+psycopg://${BASH_REMATCH[1]}"
    elif [[ ! "$CLEANED" =~ ^postgresql\+psycopg:// ]]; then
        CLEANED="postgresql+psycopg://$CLEANED"
    fi

    if [[ "$CLEANED" =~ sslmode= ]]; then
        CLEANED="$(echo "$CLEANED" | sed -E 's/sslmode=[^&]+/sslmode=require/')"
    elif [[ "$CLEANED" == *\?* ]]; then
        CLEANED="${CLEANED}&sslmode=require"
    else
        CLEANED="${CLEANED}?sslmode=require"
    fi

    echo "$CLEANED"
fi
