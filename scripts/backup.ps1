# ==============================================================================
# SpareHub - Production Backup Script for Windows / PowerShell
# ==============================================================================
[CmdletBinding()]
param(
    [string]$DbContainer = "sparehub_prod_db",
    [string]$BackendContainer = "sparehub_prod_backend",
    [int]$RetentionDays = 14
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackupDir = Join-Path $ProjectRoot "backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

Write-Host "[INFO] Starting SpareHub backup at $Timestamp..." -ForegroundColor Cyan

# 1. Verify container status
$runningContainers = docker ps --format "{{.Names}}"
if ($runningContainers -notcontains $DbContainer) {
    Write-Error "[ERROR] Database container '$DbContainer' is not running."
}
if ($runningContainers -notcontains $BackendContainer) {
    Write-Error "[ERROR] Backend container '$BackendContainer' is not running."
}

# 2. Database Backup (pg_dump custom format -Fc)
$DbBackupFile = Join-Path $BackupDir "sparehub_db_${Timestamp}.dump"
$TmpContainerDump = "/tmp/backup_${Timestamp}.dump"

Write-Host "[INFO] Dumping PostgreSQL database from $DbContainer..." -ForegroundColor Yellow
docker exec $DbContainer sh -c "pg_dump -U ""`$POSTGRES_USER"" -Fc -f '$TmpContainerDump' ""`$POSTGRES_DB"""
docker cp "${DbContainer}:${TmpContainerDump}" $DbBackupFile
docker exec $DbContainer rm -f $TmpContainerDump

$dbSize = (Get-Item $DbBackupFile).Length / 1KB
Write-Host "[SUCCESS] Database backup saved: $DbBackupFile ($([math]::Round($dbSize, 2)) KB)" -ForegroundColor Green

# 3. Media Uploads Archive (tar.gz)
$UploadsBackupFile = Join-Path $BackupDir "sparehub_uploads_${Timestamp}.tar.gz"
$TmpContainerTar = "/tmp/uploads_${Timestamp}.tar.gz"

Write-Host "[INFO] Creating media uploads archive from $BackendContainer..." -ForegroundColor Yellow
docker exec $BackendContainer tar -czf $TmpContainerTar -C /app uploads
docker cp "${BackendContainer}:${TmpContainerTar}" $UploadsBackupFile
docker exec $BackendContainer rm -f $TmpContainerTar

$uploadsSize = (Get-Item $UploadsBackupFile).Length / 1KB
Write-Host "[SUCCESS] Uploads backup saved: $UploadsBackupFile ($([math]::Round($uploadsSize, 2)) KB)" -ForegroundColor Green

# 4. Retention Policy: Retain backups for 14 days
Write-Host "[INFO] Cleaning up backups older than $RetentionDays days..." -ForegroundColor Yellow
$Cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupDir -Filter "sparehub_*" | Where-Object { $_.LastWriteTime -lt $Cutoff } | Remove-Item -Force

Write-Host "[DONE] SpareHub backup completed successfully." -ForegroundColor Green

