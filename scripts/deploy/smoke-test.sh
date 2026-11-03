#!/usr/bin/env bash
# ==============================================================================
# smoke-test.sh: Verifies deployed SpareHub frontend, API proxy, and database.
#
# Usage:
#   ./scripts/deploy/smoke-test.sh https://your-project.vercel.app
#
# Checks:
#   1. Frontend SPA root: GET / (status 200 and HTML index)
#   2. API Health:        GET /api/health (retrying up to 90s for Render cold start)
#   3. DB Health:         GET /api/health/db (validates Neon PostgreSQL connection)
# ==============================================================================
set -euo pipefail

TARGET_URL="${1:-}"
if [[ -z "$TARGET_URL" ]]; then
    read -r -p "Enter deployed frontend URL (e.g. https://your-app.vercel.app): " TARGET_URL
fi

# Clean trailing slashes and ensure https://
TARGET_URL="$(echo "$TARGET_URL" | sed 's:/*$::')"
if [[ ! "$TARGET_URL" =~ ^https?:// ]]; then
    TARGET_URL="https://$TARGET_URL"
fi

echo "================================================================="
echo "  SpareHub Smoke Test - Target: $TARGET_URL"
echo "================================================================="

FRONTEND_STATUS="FAIL"
API_STATUS="FAIL"
DB_STATUS="FAIL"

# 1. Frontend Check
echo -n "[CHECK 1/3] Frontend SPA root ($TARGET_URL)... "
HTTP_CODE=$(curl -s -o /tmp/sparehub_fe.html -w "%{http_code}" "$TARGET_URL" || true)
if [[ "$HTTP_CODE" == "200" ]] && grep -qi -E "(root|vite|sparehub|<html)" /tmp/sparehub_fe.html 2>/dev/null; then
    FRONTEND_STATUS="PASS"
    echo "PASS (HTTP 200)"
else
    echo "FAIL (HTTP $HTTP_CODE)"
fi
rm -f /tmp/sparehub_fe.html

# 2. API Health Check (with cold-start retry up to 90 seconds)
echo "[CHECK 2/3] API Health ($TARGET_URL/api/health)..."
echo "            (Waiting up to 90s to allow for Render free tier container cold start)"

MAX_ATTEMPTS=18
SLEEP_SECS=5
ATTEMPT=1
API_URL="$TARGET_URL/api/health"

while [[ $ATTEMPT -le $MAX_ATTEMPTS ]]; do
    RESPONSE_FILE=$(mktemp)
    HTTP_CODE=$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" --max-time 15 "$API_URL" || true)
    BODY=$(cat "$RESPONSE_FILE" 2>/dev/null || true)
    rm -f "$RESPONSE_FILE"

    if [[ "$HTTP_CODE" == "200" ]] && echo "$BODY" | grep -qi -E "(ok|healthy)"; then
        API_STATUS="PASS"
        echo "            -> PASS (attempt $ATTEMPT/$MAX_ATTEMPTS: HTTP 200 OK)"
        break
    else
        echo "            -> [Attempt $ATTEMPT/$MAX_ATTEMPTS] Backend waking up... (HTTP $HTTP_CODE). Retrying in ${SLEEP_SECS}s..."
        sleep "$SLEEP_SECS"
        ATTEMPT=$((ATTEMPT + 1))
    fi
done

if [[ "$API_STATUS" != "PASS" ]]; then
    echo "            -> FAIL: Backend did not report healthy within 90s."
fi

# 3. DB Health Check
echo "[CHECK 3/3] DB Health ($TARGET_URL/api/health/db)..."
DB_URL="$TARGET_URL/api/health/db"
DB_ATTEMPTS=6
DB_ATTEMPT=1

while [[ $DB_ATTEMPT -le $DB_ATTEMPTS ]]; do
    RESPONSE_FILE=$(mktemp)
    HTTP_CODE=$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" --max-time 15 "$DB_URL" || true)
    BODY=$(cat "$RESPONSE_FILE" 2>/dev/null || true)
    rm -f "$RESPONSE_FILE"

    if [[ "$HTTP_CODE" == "200" ]] && echo "$BODY" | grep -qi -E "(ok|healthy|connected)"; then
        DB_STATUS="PASS"
        echo "            -> PASS (attempt $DB_ATTEMPT/$DB_ATTEMPTS: HTTP 200 OK)"
        break
    else
        echo "            -> [Attempt $DB_ATTEMPT/$DB_ATTEMPTS] DB connecting... (HTTP $HTTP_CODE). Retrying in 5s..."
        sleep 5
        DB_ATTEMPT=$((DB_ATTEMPT + 1))
    fi
done

if [[ "$DB_STATUS" != "PASS" ]]; then
    echo "            -> FAIL: Database health check failed."
fi

# Print Final Summary
echo ""
echo "================================================================="
echo "  Smoke Test Results Summary"
echo "================================================================="
echo "  Frontend SPA Index:   [$FRONTEND_STATUS] $TARGET_URL/"
echo "  Backend API Health:   [$API_STATUS] $TARGET_URL/api/health"
echo "  Database Connection:  [$DB_STATUS] $TARGET_URL/api/health/db"
echo "================================================================="

if [[ "$FRONTEND_STATUS" == "PASS" && "$API_STATUS" == "PASS" && "$DB_STATUS" == "PASS" ]]; then
    echo "RESULT: ALL CHECKS PASSED!"
    exit 0
else
    echo "RESULT: ONE OR MORE CHECKS FAILED."
    echo ""
    echo "Troubleshooting Tips:"
    if [[ "$FRONTEND_STATUS" != "PASS" ]]; then
        echo " - Frontend: Verify Vercel build output is 'dist' and build command is 'npm run build'."
    fi
    if [[ "$API_STATUS" != "PASS" ]]; then
        echo " - API: Check frontend/vercel.json rewrite destination matches your Render service URL."
        echo " - API: Check Render service logs in the Render dashboard for startup or crash errors."
    fi
    if [[ "$DB_STATUS" != "PASS" ]]; then
        echo " - DB: Verify DATABASE_URL in Render is postgresql+psycopg:// with ?sslmode=require."
        echo " - DB: Verify Alembic migrations executed successfully (alembic upgrade head)."
    fi
    exit 1
fi
