<#
.SYNOPSIS
    Runs the interactive admin creation CLI against a remote database (e.g., Neon PostgreSQL).
.DESCRIPTION
    Sets all environment variables required by SpareHub's configuration validator
    (DATABASE_URL, SECRET_KEY, APP_ENV, CORS_ORIGINS) and runs
    python -m app.scripts.create_admin in /backend.
.PARAMETER EmployeeId
    Admin employee ID (e.g. ADM001). Prompted if omitted.
.PARAMETER Name
    Admin full name. Prompted if omitted.
.PARAMETER Email
    Admin email address. Prompted if omitted.
.PARAMETER LocationCode
    Store location code (e.g. BLR). Prompted if omitted.
.PARAMETER DatabaseUrl
    Remote Neon PostgreSQL connection string. Prompted if omitted.
.EXAMPLE
    .\scripts\deploy\create-admin-remote.ps1
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$EmployeeId,

    [Parameter(Mandatory = $false)]
    [string]$Name,

    [Parameter(Mandatory = $false)]
    [string]$Email,

    [Parameter(Mandatory = $false)]
    [string]$LocationCode,

    [Parameter(Mandatory = $false)]
    [string]$DatabaseUrl
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path "$scriptDir\..\..").Path
$backendDir = Join-Path $repoRoot "backend"

# Check for .env.deploy.local if DatabaseUrl is not provided
$deployEnvFile = Join-Path $repoRoot ".env.deploy.local"
if (-not $DatabaseUrl -and (Test-Path $deployEnvFile)) {
    Write-Host "[INFO] Loading configuration from .env.deploy.local..." -ForegroundColor Cyan
    Get-Content $deployEnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $varName = $parts[0].Trim()
            $varVal = $parts[1].Trim()
            if ($varName -eq "DATABASE_URL" -or $varName -eq "REMOTE_DATABASE_URL") {
                $DatabaseUrl = $varVal
            }
        }
    }
}

if (-not $DatabaseUrl) {
    Write-Host "=================================================================" -ForegroundColor Yellow
    Write-Host "  SpareHub - Remote Store Admin Creation CLI" -ForegroundColor Yellow
    Write-Host "=================================================================" -ForegroundColor Yellow
    Write-Host "Please enter the remote Neon PostgreSQL connection string."
    Write-Host "(Input is masked for security)"
    $secureDbUrl = Read-Host "Enter remote DATABASE_URL" -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureDbUrl)
    $DatabaseUrl = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if (-not $DatabaseUrl -or $DatabaseUrl.Trim() -eq "") {
    Write-Error "DATABASE_URL cannot be empty."
    exit 1
}

# Convert scheme using neon-url.ps1
$convertedDbUrl = & "$scriptDir\neon-url.ps1" -Url $DatabaseUrl
if (-not $convertedDbUrl) {
    Write-Error "Failed to process DATABASE_URL."
    exit 1
}

if (-not $EmployeeId) {
    $EmployeeId = Read-Host "Enter Admin Employee ID [e.g. ADM001]"
}
if (-not $Name) {
    $Name = Read-Host "Enter Admin Full Name"
}
if (-not $Email) {
    $Email = Read-Host "Enter Admin Email"
}
if (-not $LocationCode) {
    $LocationCode = Read-Host "Enter Store Location Code [e.g. BLR]"
}

$LocationCode = $LocationCode.Trim().ToUpper()
$EmployeeId = $EmployeeId.Trim().ToUpper()

# Generate temporary secret key for configuration validator if not set
$secretKey = & "$scriptDir\gen-secret.ps1"

# Set environment variables for the python child process
$env:DATABASE_URL = $convertedDbUrl
$env:APP_ENV = "production"
$env:APP_TIMEZONE = "Asia/Kolkata"
$env:CORS_ORIGINS = "https://admin.sparehub.internal"
$env:SECRET_KEY = $secretKey
$env:SEED_DEFAULT_PASSWORD = ""

Write-Host "[INFO] Verifying location '$LocationCode' in remote database..." -ForegroundColor Cyan

# Pre-verify and initialize location if absent
Push-Location $backendDir
try {
    python -c @"
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
            name=f'ITC {loc_code}',
            code=loc_code,
            city='Main Facility',
            is_active=True
        )
        db.add(new_loc)
        db.commit()
        print(f"[SUCCESS] Initialized location '{loc_code}'.")
    else:
        print(f"[INFO] Location '{loc_code}' ({loc.name}) confirmed.")
finally:
    db.close()
"@ "$LocationCode"

    Write-Host "[INFO] Running python -m app.scripts.create_admin..." -ForegroundColor Green
    python -m app.scripts.create_admin `
        --employee-id "$EmployeeId" `
        --name "$Name" `
        --email "$Email" `
        --location-code "$LocationCode"
}
finally {
    Pop-Location
}
