#!/usr/bin/env bash
# ==============================================================================
# SpareHub - Production Backup Script (PostgreSQL custom format + Uploads tar)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

DB_CONTAINER="${DB_CONTAINER:-sparehub_prod_db}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-sparehub_prod_backend}"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting SpareHub backup at ${TIMESTAMP}..."

# 1. Verify container availability
if ! docker ps --format '{{.Names}}' | grep -Eq "^${DB_CONTAINER}\$"; then
    echo "[ERROR] Database container '${DB_CONTAINER}' is not running." >&2
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -Eq "^${BACKEND_CONTAINER}\$"; then
    echo "[ERROR] Backend container '${BACKEND_CONTAINER}' is not running." >&2
    exit 1
fi

# 2. Database Backup (pg_dump custom format -Fc)
DB_BACKUP_FILE="${BACKUP_DIR}/sparehub_db_${TIMESTAMP}.dump"
TMP_CONTAINER_DUMP="/tmp/backup_${TIMESTAMP}.dump"

echo "[INFO] Creating PostgreSQL database dump from ${DB_CONTAINER}..."
docker exec "${DB_CONTAINER}" sh -c "pg_dump -U \"\${POSTGRES_USER}\" -Fc -f '${TMP_CONTAINER_DUMP}' \"\${POSTGRES_DB}\""
docker cp "${DB_CONTAINER}:${TMP_CONTAINER_DUMP}" "${DB_BACKUP_FILE}"
docker exec "${DB_CONTAINER}" rm -f "${TMP_CONTAINER_DUMP}"

echo "[SUCCESS] Database backup saved: ${DB_BACKUP_FILE} ($(du -h "${DB_BACKUP_FILE}" | cut -f1))"

# 3. Media Uploads Archive (tar.gz)
UPLOADS_BACKUP_FILE="${BACKUP_DIR}/sparehub_uploads_${TIMESTAMP}.tar.gz"
TMP_CONTAINER_TAR="/tmp/uploads_${TIMESTAMP}.tar.gz"

echo "[INFO] Creating media uploads archive from ${BACKEND_CONTAINER}..."
docker exec "${BACKEND_CONTAINER}" tar -czf "${TMP_CONTAINER_TAR}" -C /app uploads
docker cp "${BACKEND_CONTAINER}:${TMP_CONTAINER_TAR}" "${UPLOADS_BACKUP_FILE}"
docker exec "${BACKEND_CONTAINER}" rm -f "${TMP_CONTAINER_TAR}"

echo "[SUCCESS] Uploads backup saved: ${UPLOADS_BACKUP_FILE} ($(du -h "${UPLOADS_BACKUP_FILE}" | cut -f1))"

# 4. Retention Policy: Retain backups for 14 days
echo "[INFO] Cleaning up backups older than 14 days..."
find "${BACKUP_DIR}" -name "sparehub_*" -type f -mtime +14 -exec rm -f {} \; || true

echo "[DONE] Backup completed successfully at $(date +%Y-%m-%d\ %H:%M:%S)."

