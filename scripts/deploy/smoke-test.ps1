<#
.SYNOPSIS
    Runs smoke tests against the deployed SpareHub frontend, API proxy, and database.
.DESCRIPTION
    Tests:
    1. Frontend SPA root (status 200 and HTML index)
    2. API Health: GET /api/health (retrying up to 90s for Render cold start)
    3. DB Health: GET /api/health/db (validates Neon PostgreSQL connection)
.PARAMETER Url
    The deployed Vercel frontend URL (e.g. https://your-project.vercel.app).
.EXAMPLE
    .\scripts\deploy\smoke-test.ps1 -Url "https://sparehub.vercel.app"
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $false)]
    [string]$Url
)

$ErrorActionPreference = "Continue"

if (-not $Url -or $Url.Trim() -eq "") {
    $Url = Read-Host "Enter deployed frontend URL (e.g. https://your-app.vercel.app)"
}

$cleanUrl = $Url.Trim().TrimEnd('/')
if (-not ($cleanUrl -match "^https?://")) {
    $cleanUrl = "https://$cleanUrl"
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  SpareHub Smoke Test - Target: $cleanUrl" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$frontendStatus = "FAIL"
$apiStatus = "FAIL"
$dbStatus = "FAIL"

# 1. Frontend Check
Write-Host -NoNewline "[CHECK 1/3] Frontend SPA root ($cleanUrl)... "
try {
    $feResponse = Invoke-WebRequest -Uri "$cleanUrl/" -UseBasicParsing -TimeoutSec 15
    if ($feResponse.StatusCode -eq 200 -and ($feResponse.Content -match "(root|vite|sparehub|<html)")) {
        $frontendStatus = "PASS"
        Write-Host "PASS (HTTP 200)" -ForegroundColor Green
    } else {
        Write-Host "FAIL (HTTP $($feResponse.StatusCode))" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL ($_)" -ForegroundColor Red
}

# 2. API Health Check (with cold-start retry up to 90 seconds)
Write-Host "[CHECK 2/3] API Health ($cleanUrl/api/health)..."
Write-Host "            (Waiting up to 90s to allow for Render free tier container cold start)" -ForegroundColor DarkGray

$maxAttempts = 18
$sleepSecs = 5
$apiUrl = "$cleanUrl/api/health"

for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    try {
        $apiResp = Invoke-WebRequest -Uri $apiUrl -UseBasicParsing -TimeoutSec 15
        if ($apiResp.StatusCode -eq 200 -and ($apiResp.Content -match "(ok|healthy)")) {
            $apiStatus = "PASS"
            Write-Host "            -> PASS (attempt $attempt/${maxAttempts}: HTTP 200 OK)" -ForegroundColor Green
            break
        } else {
            Write-Host "            -> [Attempt $attempt/$maxAttempts] Backend waking up... (HTTP $($apiResp.StatusCode)). Retrying in ${sleepSecs}s..." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "            -> [Attempt $attempt/$maxAttempts] Backend waking up... Retrying in ${sleepSecs}s..." -ForegroundColor Yellow
    }
    Start-Sleep -Seconds $sleepSecs
}

if ($apiStatus -ne "PASS") {
    Write-Host "            -> FAIL: Backend did not report healthy within 90s." -ForegroundColor Red
}

# 3. DB Health Check
Write-Host "[CHECK 3/3] DB Health ($cleanUrl/api/health/db)..."
$dbUrl = "$cleanUrl/api/health/db"
$dbMaxAttempts = 6

for ($dbAttempt = 1; $dbAttempt -le $dbMaxAttempts; $dbAttempt++) {
    try {
        $dbResp = Invoke-WebRequest -Uri $dbUrl -UseBasicParsing -TimeoutSec 15
        if ($dbResp.StatusCode -eq 200 -and ($dbResp.Content -match "(ok|healthy|connected)")) {
            $dbStatus = "PASS"
            Write-Host "            -> PASS (attempt $dbAttempt/${dbMaxAttempts}: HTTP 200 OK)" -ForegroundColor Green
            break
        } else {
            Write-Host "            -> [Attempt $dbAttempt/$dbMaxAttempts] DB connecting... Retrying in 5s..." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "            -> [Attempt $dbAttempt/$dbMaxAttempts] DB connecting... Retrying in 5s..." -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 5
}

if ($dbStatus -ne "PASS") {
    Write-Host "            -> FAIL: Database health check failed." -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Smoke Test Results Summary" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Frontend SPA Index:   [$frontendStatus] $cleanUrl/"
Write-Host "  Backend API Health:   [$apiStatus] $cleanUrl/api/health"
Write-Host "  Database Connection:  [$dbStatus] $cleanUrl/api/health/db"
Write-Host "=================================================================" -ForegroundColor Cyan

if ($frontendStatus -eq "PASS" -and $apiStatus -eq "PASS" -and $dbStatus -eq "PASS") {
    Write-Host "RESULT: ALL CHECKS PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "RESULT: ONE OR MORE CHECKS FAILED." -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting Tips:" -ForegroundColor Yellow
    if ($frontendStatus -ne "PASS") {
        Write-Host " - Frontend: Verify Vercel build output is 'dist' and build command is 'npm run build'."
    }
    if ($apiStatus -ne "PASS") {
        Write-Host " - API: Check frontend/vercel.json rewrite destination matches your Render service URL."
        Write-Host " - API: Check Render service logs in the Render dashboard for startup or crash errors."
    }
    if ($dbStatus -ne "PASS") {
        Write-Host " - DB: Verify DATABASE_URL in Render is postgresql+psycopg:// with ?sslmode=require."
        Write-Host " - DB: Verify Alembic migrations executed successfully (alembic upgrade head)."
    }
    exit 1
}
