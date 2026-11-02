#!/usr/bin/env bash
# ==============================================================================
# create-admin-remote.sh: Runs the interactive admin creation CLI against a remote
#                         database (e.g., Neon PostgreSQL).
#
# Usage:
#   ./scripts/deploy/create-admin-remote.sh
#   # Or with arguments:
#   ./scripts/deploy/create-admin-remote.sh --employee-id ADM001 --name "Admin User" --email admin@example.com --location-code BLR
#
# Config:
#   Can read DATABASE_URL from .env.deploy.local in the repo root if present.
#   Otherwise prompts for values securely. Never echoes secrets.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Find python executable
if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1 && python -c "import sys" >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "[ERROR] Python 3 is required to run this script." >&2
    exit 1
fi

# Load from gitignored .env.deploy.local if present
DEPLOY_LOCAL_ENV="$REPO_ROOT/.env.deploy.local"
if [[ -f "$DEPLOY_LOCAL_ENV" ]]; then
    echo "[INFO] Loading configuration from .env.deploy.local..."
    set -a
    # shellcheck disable=SC1090
    source "$DEPLOY_LOCAL_ENV"
    set +a
fi

# Resolve remote DATABASE_URL
DB_URL="${DATABASE_URL:-${REMOTE_DATABASE_URL:-}}"
if [[ -z "$DB_URL" ]]; then
    echo "================================================================="
    echo "  SpareHub - Remote Store Admin Creation CLI"
    echo "================================================================="
    echo "Please provide your remote Neon PostgreSQL connection URL."
    echo "(Input will NOT be echoed on the screen for security)"
    echo -n "Enter remote DATABASE_URL: "
    read -r -s DB_URL
    echo ""
fi

# Convert scheme and ensure sslmode=require if needed
if [[ -n "$DB_URL" ]]; then
    DB_URL="$("$SCRIPT_DIR/neon-url.sh" "$DB_URL")"
fi

if [[ -z "$DB_URL" ]]; then
    echo "[ERROR] DATABASE_URL cannot be empty." >&2
    exit 1
fi

# Set required environment variables to satisfy app/core/config.py validation in production mode
export DATABASE_URL="$DB_URL"
export APP_ENV="${APP_ENV:-production}"
export APP_TIMEZONE="${APP_TIMEZONE:-Asia/Kolkata}"
export CORS_ORIGINS="${CORS_ORIGINS:-https://admin.sparehub.internal}"
export SEED_DEFAULT_PASSWORD=""

# Generate a temporary >=32 char SECRET_KEY for config validator if not provided
if [[ -z "${SECRET_KEY:-}" ]] || [[ "${#SECRET_KEY}" -lt 32 ]] || [[ "$SECRET_KEY" == *"placeholder"* ]]; then
    export SECRET_KEY="$("$SCRIPT_DIR/gen-secret.sh")"
fi

# Parse any CLI arguments passed or prompt for admin details
EMP_ID=""
ADMIN_NAME=""
ADMIN_EMAIL=""
LOC_CODE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --employee-id)
            EMP_ID="$2"
            shift 2
            ;;
        --name)
            ADMIN_NAME="$2"
            shift 2
            ;;
        --email)
            ADMIN_EMAIL="$2"
            shift 2
            ;;
        --location-code)
            LOC_CODE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [[ -z "$EMP_ID" ]]; then
    read -r -p "Enter Admin Employee ID [e.g. ADM001]: " EMP_ID
fi

if [[ -z "$ADMIN_NAME" ]]; then
    read -r -p "Enter Admin Full Name: " ADMIN_NAME
fi

if [[ -z "$ADMIN_EMAIL" ]]; then
    read -r -p "Enter Admin Email: " ADMIN_EMAIL
fi

if [[ -z "$LOC_CODE" ]]; then
    read -r -p "Enter Store Location Code [e.g. BLR]: " LOC_CODE
fi

LOC_CODE="$(echo "$LOC_CODE" | tr '[:lower:]' '[:upper:]' | xargs)"
EMP_ID="$(echo "$EMP_ID" | tr '[:lower:]' '[:upper:]' | xargs)"

# Ensure location exists in the remote database (creating it if needed)
echo "[INFO] Verifying location '$LOC_CODE' in remote database..."
(
    cd "$REPO_ROOT/backend"
    "$PY_BIN" - "$LOC_CODE" << 'EOF'
import sys
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.location import Location

loc_code = sys.argv[1].strip()
db = SessionLocal()
try:
    loc = db.scalar(select(Location).where(Location.code == loc_code))
    if not loc:
        print(f"[INFO] Location '{loc_code}' does not exist yet. Initializing location record...")
        new_loc = Location(
            name=f"ITC {loc_code}",
            code=loc_code,
            city="Main Facility",
            is_active=True
        )
        db.add(new_loc)
        db.commit()
        print(f"[SUCCESS] Initialized location '{loc_code}'.")
    else:
        print(f"[INFO] Location '{loc_code}' ({loc.name}) confirmed.")
finally:
    db.close()
EOF
)

# Run interactive create_admin script
echo "[INFO] Running python -m app.scripts.create_admin..."
(
    cd "$REPO_ROOT/backend"
    "$PY_BIN" -m app.scripts.create_admin \
        --employee-id "$EMP_ID" \
        --name "$ADMIN_NAME" \
        --email "$ADMIN_EMAIL" \
        --location-code "$LOC_CODE"
)
