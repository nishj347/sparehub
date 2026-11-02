<#
.SYNOPSIS
    Generates a cryptographically secure 32+ character SECRET_KEY for SpareHub production.
.DESCRIPTION
    Generates a random token using Python secrets module if available, or .NET
    RandomNumberGenerator as a fallback.
.EXAMPLE
    .\scripts\deploy\gen-secret.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

try {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
        if ($secret -and $secret.Trim().Length -ge 32) {
            Write-Output $secret.Trim()
            exit 0
        }
    }

    # .NET Cryptography Fallback
    $bytes = [byte[]]::new(36)
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_').TrimEnd('=')
    Write-Output $secret
}
catch {
    Write-Error "Failed to generate secret key: $_"
    exit 1
}
