param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [int]$StartupTimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$probePath = Join-Path $repoRoot "scripts\probe_avatar_motion_lab.ps1"
$baseUrl = "http://$HostName`:$Port"

function Test-PubCastHealth {
    param([Parameter(Mandatory = $true)][string]$Url)

    try {
        Invoke-RestMethod -Method GET -Uri "$Url/health" -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Could not find venv Python at $pythonPath"
}

if (-not (Test-Path -LiteralPath $probePath)) {
    throw "Could not find probe script at $probePath"
}

Set-Location $repoRoot

$serverProcess = $null
$startedServer = $false

try {
    if (Test-PubCastHealth -Url $baseUrl) {
        Write-Host "PubCast already responding at $baseUrl"
    }
    else {
        $logDir = Join-Path $repoRoot "logs"
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null

        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $stdoutLog = Join-Path $logDir "avatar_motion_lab_uvicorn_$stamp.out.log"
        $stderrLog = Join-Path $logDir "avatar_motion_lab_uvicorn_$stamp.err.log"

        Write-Host "Starting PubCast at $baseUrl"
        Write-Host "Server logs:"
        Write-Host "  $stdoutLog"
        Write-Host "  $stderrLog"

        $serverProcess = Start-Process `
            -FilePath $pythonPath `
            -ArgumentList @("-m", "uvicorn", "main:app", "--host", $HostName, "--port", "$Port") `
            -WorkingDirectory $repoRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog `
            -PassThru

        $startedServer = $true

        $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
        while ((Get-Date) -lt $deadline) {
            if ($serverProcess.HasExited) {
                throw "PubCast exited before /health became ready. Check $stderrLog"
            }

            if (Test-PubCastHealth -Url $baseUrl) {
                Write-Host "PubCast is ready."
                break
            }

            Start-Sleep -Seconds 1
        }

        if (-not (Test-PubCastHealth -Url $baseUrl)) {
            throw "Timed out waiting for PubCast at $baseUrl. Check $stderrLog"
        }
    }

    powershell -ExecutionPolicy Bypass -File $probePath -BaseUrl $baseUrl
    Write-Host "One-command avatar motion lab probe finished."
}
finally {
    if ($startedServer -and $null -ne $serverProcess -and -not $serverProcess.HasExited) {
        Write-Host "Stopping temporary PubCast server."
        Stop-Process -Id $serverProcess.Id
    }
}
