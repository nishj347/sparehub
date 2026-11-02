<#
.SYNOPSIS
    Converts a Neon PostgreSQL URL to the postgresql+psycopg:// scheme with sslmode=require.
.DESCRIPTION
    FastAPI and SQLAlchemy in SpareHub require psycopg v3 (postgresql+psycopg://) and
    encrypted SSL connections (sslmode=require) for Neon PostgreSQL.
.PARAMETER Url
    The raw connection string provided by Neon (starts with postgresql:// or postgres://).
.EXAMPLE
    .\scripts\deploy\neon-url.ps1 -Url "postgresql://user:pass@ep-cool-123.neon.tech/neondb?sslmode=require"
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $false)]
    [string]$Url
)

$ErrorActionPreference = "Stop"

if (-not $Url -or $Url.Trim() -eq "") {
    $Url = Read-Host "Enter Neon PostgreSQL connection string"
}

$clean = $Url.Trim()
if (-not $clean) {
    Write-Error "No connection string provided."
    exit 1
}

# Try Python if available for exact URL parsing
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        $converted = python -c @"
import sys
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

raw = sys.argv[1].strip()
if raw.startswith('postgres://'):
    raw = 'postgresql://' + raw[len('postgres://'):]
elif not (raw.startswith('postgresql://') or raw.startswith('postgresql+psycopg://')):
    raw = 'postgresql://' + raw

parsed = urlparse(raw)
query_dict = dict(parse_qsl(parsed.query, keep_blank_values=True))
query_dict['sslmode'] = 'require'
new_query = urlencode(query_dict)

converted = urlunparse((
    'postgresql+psycopg',
    parsed.netloc,
    parsed.path,
    parsed.params,
    new_query,
    ''
))
print(converted)
"@ "$clean"

        if ($converted -and $converted.Trim().StartsWith("postgresql+psycopg://")) {
            Write-Output $converted.Trim()
            exit 0
        }
    } catch {
        # Fall back to PowerShell regex processing
    }
}

# PowerShell regex conversion fallback
if ($clean -match "^postgres://(.*)$") {
    $clean = "postgresql+psycopg://" + $Matches[1]
} elseif ($clean -match "^postgresql://(.*)$") {
    $clean = "postgresql+psycopg://" + $Matches[1]
} elseif (-not ($clean.StartsWith("postgresql+psycopg://"))) {
    $clean = "postgresql+psycopg://" + $clean
}

if ($clean -match "sslmode=[^&]+") {
    $clean = $clean -replace "sslmode=[^&]+", "sslmode=require"
} elseif ($clean.Contains("?")) {
    $clean = $clean + "&sslmode=require"
} else {
    $clean = $clean + "?sslmode=require"
}

Write-Output $clean
